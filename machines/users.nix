{ ... }:
{
    imports = [ ./passwords.nix ];

    users.mutableUsers = false;
    users.users.root = {
        # root password is stored in hardware-configuration.nix, passwords.nix
        home = "/root";
        openssh.authorizedKeys.keys = [''
            ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIMJB1wOikViWvuBvrui79oTASXFYiRorsNYL7oovZBVP emarioo@nixos''
        ];
    };
    users.users.emarioo = {
        home = "/home/emarioo";
        isNormalUser = true;
        extraGroups = [ "wheel" ]; # Enable ‘sudo’ for the user.
        openssh.authorizedKeys.keys = [''
            ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIMJB1wOikViWvuBvrui79oTASXFYiRorsNYL7oovZBVP emarioo@nixos''
        ];
    };
}