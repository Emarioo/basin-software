#!/usr/bin/env python3

'''
This script is based on https://github.com/elitak/nixos-infect
    and https://github.com/notthebee/nixos-infect (hostinger tweaks)

Changes made:
    - bash -> python
    - merged networking.nix and hardware-configuration-nix
    - curl is mandatory, curl is no longer faked with wget
    - Seperated fetch and infect code.
     
Options
    --dry-run
    --no-reboot
    --network-config
    --provider <hostinger|lightsail|...>

The refactor from bash to python may have introduced bugs.

The script has been tested on:
- Ubuntu, Hostinger
'''

import os, subprocess, dataclasses, shlex, re, sys, glob, shutil

@dataclasses.dataclass
class Options:
    detailed_network: bool = False
    provider: str = ""
    dry_run: bool = False
    has_root_password_or_auth_keys: bool = False
    force: bool = False

def run_ignore(cmd):
    os.system(cmd)

def run(cmd):
    print(cmd)
    proc = subprocess.run(cmd, shell=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if proc.returncode != 0:
        print(proc.stdout)
        exit(1)
    print(proc.stdout)
    return proc.stdout.strip()


def run_noret(cmd):
    print(cmd)
    proc = subprocess.run(cmd, shell=True, text=True)
    if proc.returncode != 0:
        exit(1)

def source_env(script):
    print(cmd)
    proc = subprocess.run("env", shell=True, executable="/usr/bin/bash", text=True, stdout=subprocess.PIPE)
    prev = proc.stdout
    cmd = f'source "{script}" > /dev/null && env'
    proc = subprocess.run(cmd, shell=True, executable="/usr/bin/bash", text=True, stdout=subprocess.PIPE)
    out = proc.stdout
    if proc.returncode != 0:
        print(out)
        exit(1)
    # new_env = set(out.splitlines()) - set(prev.splitlines())
    # print("\n".join(list(new_env)))
    for line in out.splitlines():
        k, _, v = line.partition("=")
        os.environ[k] = v

def isX86_64():
    return run("uname -m") == "x86_64"

def isEFI():
    return os.path.isdir("/sys/firmware/efi")

rootfsdev = ""
rootfstype = ""
esp = ""
grubdev = ""
newrootfslabel = ""
NO_SWAP = False


# Fetch info from environment and return text meant as hardware-configuration-nix
# includes boot, kernal, and network settings specific to the machine
def gen_hardware_config(options: Options):

    if isEFI():
        bootcfg = f'''
    boot.loader.grub = {{
        efiSupport = true;
        efiInstallAsRemovable = true;
        device = "nodev";
    }};
    fileSystems."/boot" = {{ device = "{esp}"; fsType = "vfat"; }};
    '''
    else:
        bootcfg = f'''
    boot.loader.grub.device = "{grubdev}";
'''

    kernel_params=""
    if options.provider == "hostinger":
        kernel_params = '''
    boot.kernelParams = [
        "console=tty1"
        "console=ttyS0,115200"
    ];
'''

    availableKernelModules = '"ata_piix" "uhci_hcd" "xen_blkfront"'
    if isX86_64():
        availableKernelModules += ' "vmw_pvscsi"'

    network = ""
    if options.detailed_network:
        # XXX It'd be better if we used procfs for all this...
        eth0_name=run(''' ip address show | grep '^2:' | awk -F': ' '{print $2}' ''')
        eth0_ip4s=run(f''' ip address show dev "{eth0_name}" | grep 'inet ' | sed -r 's|.*inet ([0-9.]+)/([0-9]+).*|{{ address="\\1"; prefixLength=\\2; }}|' ''')
        eth0_ip6s=run(f''' ip address show dev "{eth0_name}" | grep 'inet6 ' | sed -r 's|.*inet6 ([0-9a-f:]+)/([0-9]+).*|{{ address="\\1"; prefixLength=\\2; }}|' || '' ''')
        gateway=run(f''' ip route show dev "{eth0_name}" | grep default | sed -r 's|default via ([0-9.]+).*|\\1|' ''')
        gateway6=run(f''' ip -6 route show dev "{eth0_name}" | grep default | sed -r 's|default via ([0-9a-f:]+).*|\\1|' || true ''')
        ether0=run(f''' ip address show dev "{eth0_name}" | grep link/ether | sed -r 's|.*link/ether ([0-9a-f:]+) .*|\\1|' ''')

        eth1_name=run(''' (ip address show | grep '^3:' | awk -F': ' '{print $2}')||true ''')
        if len(eth1_name) > 0:
            eth1_ip4s=run(f''' ip address show dev "{eth1_name}" | grep 'inet ' | sed -r 's|.*inet ([0-9.]+)/([0-9]+).*|{{ address="\\1"; prefixLength=\\2; }}|' ''')
            eth1_ip6s=run(f''' ip address show dev "{eth1_name}" | grep 'inet6 ' | sed -r 's|.*inet6 ([0-9a-f:]+)/([0-9]+).*|{{ address="\\1"; prefixLength=\\2; }}|' || '' ''')
            ether1=run(f''' ip address show dev "{eth1_name}" | grep link/ether | sed -r 's|.*link/ether ([0-9a-f:]+) .*|\\1|' ''')
            addr4 = " ".join(f'"{a}"' for a in eth1_ip4s.split("\n"))
            addr6 = " ".join(f'"{a}"' for a in eth1_ip6s.split("\n"))
            interfaces1=f'''
                {eth1_name} = {{
                    ipv4.addresses = [ {addr4} ];
                    ipv6.addresses = [ {addr6} ];
                }};
            ''' # j
            extraRules1=f"ATTR{{address}}==\"{ether1}\", NAME=\"{eth1_name}\""
        else:
            interfaces1=""
            extraRules1=""


        # SOURCE FROM BASH
        # readarray nameservers < <(grep ^nameserver /etc/resolv.conf | sed -r \
        #     -e 's/^nameserver[[:space:]]+([0-9.a-fA-F:]+).*/"\1"/' \
        #     -e 's/127[0-9.]+/8.8.8.8/' \
        #     -e 's/::1/8.8.8.8/' )
        nameservers = []
        with open("/etc/resolv.conf", "r") as f:
            for line in f:
                if not line.startswith("nameserver"):
                    continue

                # Extract IP after "nameserver"
                m = re.match(r'^nameserver\s+([0-9a-fA-F:.]+)', line)
                if not m:
                    continue

                ip = m.group(1)

                # Replace loopback IPv4 and IPv6
                if re.match(r'^127[0-9.]+$', ip) or ip == '::1':
                    ip = '8.8.8.8'

                nameservers.append(f'"{ip}"')


        if eth0_name.startswith("eth"):
            predictable_inames="usePredictableInterfaceNames = lib.mkForce false;"
        else:
            predictable_inames="usePredictableInterfaceNames = lib.mkForce true;"

        addr4 = " ".join(f"{a}" for a in eth0_ip4s.splitlines())
        addr6 = " ".join(f"{a}" for a in eth0_ip6s.splitlines())
        ns = " ".join(nameservers)
        network = f'''
    networking = {{
        hostName = "{run("hostname -s")}";
        domain = "{run("hostname -d")}";
        nameservers = [ {ns} ];
        defaultGateway = "{gateway}";
        defaultGateway6 = {{
            address = "{gateway6}";
            interface = "{eth0_name}";
        }};
        dhcpcd.enable = false;
        {predictable_inames}
        interfaces = {{
        {eth0_name} = {{
            ipv4.addresses = [ {addr4} ];
            ipv6.addresses = [ {addr6} ];
            ipv4.routes = [ {{ address = "{gateway}"; prefixLength = 32; }} ];
            ipv6.routes = [ {{ address = "{gateway6}"; prefixLength = 128; }} ];
        }};
        {interfaces1}
        }};
    }};
    services.udev.extraRules = ''
        ATTR{{address}}=="{ether0}", NAME="{eth0_name}"
        {extraRules1}
    '';
        '''

    root_hashedPassword = ""
    with open("/etc/shadow", "r") as f:
        text = f.read()

    for line in text.splitlines():
        parts = line.split(":")
        if parts[0] == "root" and parts[1]:
            root_hashedPassword = f'users.users.root.hashedPassword = "{parts[1]}";'
            options.has_root_password_or_auth_keys = True
            break


    if options.provider == "lightsail":
        # Lightsail config is not like the others
        output = f'''
{{ config, pkgs, modulesPath, lib, ... }}:
{{
  imports = [ "\${{modulesPath}}/virtualisation/amazon-image.nix" ];
  boot.loader.grub.device = lib.mkForce "/dev/nvme0n1";
  {network}
}}
        '''
    else:
        output = f'''
{{ config, pkgs, modulesPath, lib, ... }}:
{{
    imports = [ (modulesPath + "/profiles/qemu-guest.nix") ];
    {bootcfg}
    boot.tmp.cleanOnBoot = true;
    boot.initrd.availableKernelModules = [ {availableKernelModules} ];
    boot.initrd.kernelModules = [ "nvme" ];
    {kernel_params}
    fileSystems."/" = {{ device = "{rootfsdev}"; fsType = "{rootfstype}"; }};
    {swapcfg}
    zramSwap.enable = {zramswap};
    {root_hashedPassword}
    {network}
}}
'''
    
    return output

def checkExistingSwap():
  global swapcfg
  global zramswap
  global NO_SWAP
  SWAPSHOW=run("swapon --show --noheadings --raw")
  zramswap="true"
  swapcfg=""
  if len(SWAPSHOW):
    SWAP_DEVICE = SWAPSHOW.split(" ", 1)[0]
    if SWAP_DEVICE.startswith("/dev/"):
      zramswap="false"
      swapcfg=f"swapDevices = [ {{ device = \"{SWAP_DEVICE}\"; }} ];"
      NO_SWAP=True

# Generate basic configuration
def gen_config(options: Options):
        
    key_regex = re.compile(
        r'^[^#]?((sk-ssh|sk-ecdsa|ssh|ecdsa)-\S+)\s+(\S+)\s+(.*)$'
    )
    paths = set([
        "/root/.ssh/authorized_keys",
        os.path.expandvars("/home/$SUDO_USER/.ssh/authorized_keys"),
        os.path.expandvars("$HOME/.ssh/authorized_keys"),
    ])

    keys = []
    for trypath in paths:
        # print(trypath)
        if not os.path.isfile(trypath):
            continue
        with open(trypath, "r") as f:
            text = f.read()
            for line in text.split("\n"):
                m = key_regex.match(line.strip())
                # print("check",line, m)
                if m:
                    keys.append(f"{m.group(1)} {m.group(3)} {m.group(4)}")
                    options.has_root_password_or_auth_keys = True

    key_text = "".join(f"        \"{key}\"\n" for key in keys).strip()
    version = os.environ["NIX_CHANNEL"].split("-")[1]
    output = f'''
{{ ... }}:
{{
    imports = [
        /etc/nixos/hardware-configuration.nix
    ];

    services.openssh.enable = true;
    users.users.root.openssh.authorizedKeys.keys = [
        { key_text }
    ];
    
    system.stateVersion = "{version}";
}}
'''

    return output

def prepareEnv():
    global esp
    global grubdev
    global rootfsdev
    global rootfstype

    # $esp and $grubdev are used in makeConf()
    if isEFI():
        esp=""
        for d in ["/boot/EFI", "/boot/efi", "/boot"]:
            if not os.path.isdir(d):
                continue
            val = run(f''' df "{d}" --output=target | sed 1d ''')
            if d == val and len(val) > 0:
                esp = val
                break
        if len(esp) == 0:
            print("ERROR: No ESP mount point found", file=sys.stderr)
            exit(1)
        for uuid in glob.glob("/dev/disk/by-uuid/*"):
            if run(f''' readlink -f "{uuid}"''') == esp:
                print(uuid)
                break
    else:
        for dev in ["/dev/vda", "/dev/sda", "/dev/xvda", "/dev/nvme0n1"]:
            if os.path.exists(dev):
                grubdev = dev
                break

    # Retrieve root fs block device
    #                   (get root mount)  (get partition or logical volume)
    rootfsdev=run(''' mount | grep "on / type" | awk '{print $1;}' ''')
    rootfstype=run(f''' df {rootfsdev} --output=fstype | sed 1d ''')

    # DigitalOcean doesn't seem to set USER while running user data
    os.environ["USER"] = "root"
    os.environ["HOME"] = "/root"

def makeSwap():
  swapFile=run(''' mktemp /tmp/nixos-infect.XXXXX.swp ''')
  run_noret(f''' dd if=/dev/zero "of={swapFile}" bs=1M count=$((1*1024)) ''')
  run_noret(f''' chmod 0600 "{swapFile}" ''')
  run_noret(f''' mkswap "{swapFile}" ''')
  run_noret(f''' swapon -v "{swapFile}" ''')

def removeSwap():
  run_noret(''' swapoff -a ''')
  run_noret(''' rm -vf /tmp/nixos-infect.*.swp ''')


def infect(options: Options):
    global NO_SWAP
    if NO_SWAP:
        makeSwap()  # smallest (512MB) droplet needs extra memory!

    # On some versions of Oracle Linux these have the wrong permissions,
    # which stops sshd from starting when NixOS boots
    run_noret("chmod 600 /etc/ssh/ssh_host_*_key")

    # Nix installer tries to use sudo regardless of whether we're already uid 0
    #which sudo || { sudo() { eval "$@"; }; export -f sudo; }
    # shellcheck disable=SC2174
    run_noret("mkdir -p -m 0755 /nix")


    # Add nix build users
    # FIXME run only if necessary, rather than defaulting true
    run_ignore("groupadd nixbld -g 30000")
    for i in range(1, 10+1):
        run_ignore(f'''useradd -c "Nix build user {i}" -d /var/empty -g nixbld -G nixbld -M -N -r -s "{shutil.which("nologin")}" "nixbld{i}"''')
    
    # TODO use addgroup and adduser as fallbacks
    #addgroup nixbld -g 30000 || true
    #for i in {1..10}; do adduser -DH -G nixbld nixbld$i || true; done
    NIX_INSTALL_URL = os.environ.get("NIX_INSTALL_URL", "https://nixos.org/nix/install")
    run_noret(f''' curl -fL "{NIX_INSTALL_URL}" | sh -s -- --no-channel-add ''')

    # shellcheck disable=SC1090
    source_env("$HOME/.nix-profile/etc/profile.d/nix.sh")

    NIX_CHANNEL = os.environ["NIX_CHANNEL"]

    run_noret(''' nix-channel --remove nixpkgs ''')
    run_noret(f''' nix-channel --add "https://nixos.org/channels/{NIX_CHANNEL}" nixos ''')
    run_noret(''' nix-channel --update ''')

    NIXOS_CONFIG = os.environ.get("NIXOS_CONFIG","/etc/nixos/configuration.nix")
    if NIXOS_CONFIG.startswith("http"):
        run(f''' curl {NIXOS_CONFIG} -o /etc/nixos/configuration.nix ''')
        NIXOS_CONFIG = "/etc/nixos/configuration.nix"

    os.environ["NIXOS_CONFIG"] = NIXOS_CONFIG

    run_noret(f''' nix-env --set \
        -I nixpkgs={run("realpath $HOME/.nix-defexpr/channels/nixos")} \
        -f '<nixpkgs/nixos>' \
        -p /nix/var/nix/profiles/system \
        -A system ''')

    # Remove nix installed with curl | bash
    run_noret(''' rm -fv /nix/var/nix/profiles/default* ''')
    run_noret(''' /nix/var/nix/profiles/system/sw/bin/nix-collect-garbage ''')

    # Reify resolv.conf
    resolv = "/etc/resolv.conf"
    backup = "/etc/resolv.conf.lnk"
    if os.path.islink(resolv):
        shutil.move(resolv, backup)
        with open(backup, "r") as src, open(resolv, "w") as dst:
            dst.write(src.read())

    # Set label of root partition
    if len(newrootfslabel) > 0:
        print(f"Setting label of {rootfsdev} to {newrootfslabel}")
        run_noret(f''' e2label "{rootfsdev}" "{newrootfslabel}" ''')

    # Stage the Nix coup d'état
    run_noret(''' touch /etc/NIXOS ''')
    run_noret(''' echo etc/nixos                  >> /etc/NIXOS_LUSTRATE ''')
    run_noret(''' echo etc/resolv.conf            >> /etc/NIXOS_LUSTRATE ''')
    run_noret(''' echo root/.nix-defexpr/channels >> /etc/NIXOS_LUSTRATE ''')
    run_noret(''' (cd / && ls etc/ssh/ssh_host_*_key* || true) >> /etc/NIXOS_LUSTRATE ''')

    run_noret(''' rm -rf /boot.bak ''')
    if isEFI():
        run_noret(f''' umount "{esp}" ''')

    try:
        shutil.move("/boot", "/boot.bak")
    except Exception:
        run_noret(''' cp -a /boot /boot.bak ''')
        run_noret(''' rm -rf /boot/* ''')
        run_noret(''' umount /boot ''')
    
    if isEFI():
        run_noret(''' mkdir -p /boot ''')
        run_noret(f''' mount "{esp}" /boot ''')
        run_noret(''' find /boot -depth ! -path /boot -exec rm -rf {} + ''')
    
    run_noret(''' /nix/var/nix/profiles/system/bin/switch-to-configuration boot ''')

    if NO_SWAP:
        removeSwap()


def checkEnv():
    if run("whoami") != "root":
        print("ERROR: Must run as root")
        exit(1)

    # Perform some easy fixups before checking

    if shutil.which("dnf"):
        # ignore failure
        run_ignore("dnf install -y perl-Digest-SHA") # Fedora 24

    packages_to_install = []

    if not shutil.which("bzcat"):
        packages_to_install.append("bzip2")
    if not shutil.which("xzcat"):
        packages_to_install.append("xz-utils")
    if not shutil.which("curl"):
        packages_to_install.append("curl")

    if len(packages_to_install) > 0:
        print("Installing ", packages_to_install)
        if shutil.which("yum"):
            run_ignore(f"yum install -y {' '.join(packages_to_install)}")
        elif shutil.which("apt-get"):
            run_ignore("apt-get update")
            run_ignore(f"apt-get install -y {' '.join(packages_to_install)}")

    reqs = [
        "curl",
        "bzcat",
        "xzcat",
        "groupadd",
        "useradd",
        "ip",
        "awk",
        [ "cut", "df" ],
    ]

    for r in reqs:
        if type(r) is list:
            if not any(shutil.which(rl) for rl in r):
                print(f"ERROR: Missing one of these {r}")
                exit(1)
        elif shutil.which(r) is None:
            print(f"ERROR: Missing {r}")
            exit(1)

def main():
    options = Options()
    options.detailed_network = "--network-config" in sys.argv
    options.provider = sys.argv[sys.argv.index("--provider")+1] if "--provider" in sys.argv else ""
    options.dry_run = "--dry-run" in sys.argv
    options.force = "-f" in sys.argv

    if not options.dry_run and (os.path.exists("/etc/nixos/hardware-configuration.nix") and not options.force):
        print("Remove or backup /etc/nixos/hardware-configuration.nix")
        print("It will be replaced.")
        exit(1)

    if not os.environ.get("NIX_CHANNEL"):
        os.environ["NIX_CHANNEL"] = "nixos-25.11"

    if not options.provider:
        # Auto detect provider
        if os.path.exists("/etc/hetzner-build"):
            options.provider = "hetznercloud"
    
    options.provider = options.provider.lower()

    if len(options.provider) == 0:
        print("Specify '--provider hostinger' or whatever provider you use. 'generic' if your provider don't need anything special.")
        exit(1)

    global newrootfslabel
    if options.provider == "lightsail":
        newrootfslabel="nixos"

    if options.provider in [ "digitalocean", "servarica", "hetznercloud", "hostinger" ]:
        options.detailed_network = True

    # Fetch system settings

    checkEnv()
    prepareEnv()
    checkExistingSwap()

    hw_config = gen_hardware_config(options)
    sw_config = gen_config(options)

    if not options.has_root_password_or_auth_keys:
        print("Your configuration does not have:")
        print("  users.users.root.hashedPassword")
        print("     or")
        print("  users.users.root.openssh.authorizedKeys.keys")
        print()
        print("Set a root password or add key to /root/.ssh/authorized_keys")
        exit(1)

    if options.dry_run:
        print("/etc/nixos/hardware-configuration.nix:")
        print(hw_config)
        print("/etc/nixos/configuration.nix:")
        print(sw_config)

        print("done dry-run")
        exit(0)

    # Create configurations and install NixOS

    os.makedirs("/etc/nixos", exist_ok=True)
    with open("/etc/nixos/hardware-configuration.nix", "w") as f:
        f.write(hw_config)
    if not os.path.exists("/etc/nixos/configuration.nix"):
        with open("/etc/nixos/configuration.nix", "w") as f:
            f.write(sw_config)

    infect(options)

    print("NixOS infection successful!")
    print("  Consider tweaking /etc/nixos/configuration.nix")
    print("  and then reboot")

if "__main__" == __name__:
    main()
