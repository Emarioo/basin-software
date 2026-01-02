
# How to get NixOS on Hostinger

Add SSH key at `/home/root/.ssh/ed_ed25519.pub`.
Can be done in Hostinger UI too (recommended because it remains on VPS reinstalls)

Run these commands to install NixOS on the VPS.

```bash
cd /root
wget https://raw.githubusercontent.com/Emarioo/basin-software/main/nixos-infect/nixos-infect.py
nixos-infect.py --provider hostinger
reboot

rm -rf /old-root

cd /root
git clone git@github.com:Emarioo/basin-software
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

Then rebuild and we're done.
```bash
nixos-rebuild switch
```
