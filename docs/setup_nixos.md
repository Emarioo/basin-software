
# How to get NixOS on Hostinger

Uses nixos-infect by https://github.com/elitak/nixos-infect (and https://github.com/notthebee/nixos-infect for Hostinger tweaks)

First get a VPS on Hostinger.

Create ssh key on your computer if you don't have one.

Copy the public key (`/home/user/.ssh/ed_ed25519.pub`) and add to SSH keys
page in Hostinger manager for your VPS.
Alternatively login to your VPS
and add it manually to `/root/.ssh/authorized_keys`.

Run these commands to install NixOS on the VPS.
You must be root user.

```bash
wget https://raw.githubusercontent.com/Emarioo/basin-software/main/nixos-infect/nixos-infect.py
nixos-infect.py --provider hostinger
reboot
```

After reboot you should see `/nix/store` and `/etc/nixos/configuration.nix`.

There is also `/old-root` which you can remove.


# Configure VPS with NixOS

We store configurations in a repo `github.com/Emarioo/basin-software/machines/platinum/configuration.nix`.

On the VPS we clone the repo with the configs we want.
```bash
cd /root
git clone git@github.com:Emarioo/basin-software

# Or copy files instead of git clone
rsync -av --progress dev/basin-software/ root@btb-lang.org:/root/basin-software/
```

Then edit the standard configuration.nix to refer to the repo configs
```
# /etc/nixos/configuration.nix
{ ... }:
{
    imports = [
        /root/basin-software/machines/platinum/configuration.nix
    ];
}
```

Then rebuild when we change the configuration
```bash
nixos-rebuild switch
```
