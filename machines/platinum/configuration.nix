{ config, pkgs, lib, ... }:

{
    system.stateVersion = "25.11";

    imports = [
        /etc/nixos/hardware-configuration.nix
        ../generic.nix
        ../users.nix
    ];

    services.nginx = {
        enable = true;

        virtualHosts."btb-lang.org" = {
            enableACME = true;
            addSSL = true;
            locations."/".proxyPass = "http://127.0.0.1:3000";
        };

        virtualHosts."git.btb-lang.org" = {
            enableACME = true;
            onlySSL = true;
            locations."/".proxyPass = "http://127.0.0.1:9500";
        };
    };

    systemd.services.btb-website = {
        description = "BTB Website";
        after = [ "network.target" ];
        wantedBy = [ "multi-user.target" ];

        serviceConfig = {
            User = "btbwebsite";
            Group = "btbwebsite";
            WorkingDirectory = "/srv/btbwebsite/btb-website";

            # @TODO Don't hardcode nodejs version?
            ExecStart = "${pkgs.nodePackages.nodejs}/bin/node server.js";

            Restart = "always";
            Environment = [
                "NODE_ENV=production"
                "PORT=3000"
            ];
        };
    };
    users.users.btbwebsite = {
        isSystemUser = true;
        group = "btbwebsite";
        home = "/srv/btbwebsite";
    };

    users.groups.btbwebsite = {};

    systemd.tmpfiles.rules = [
        "d /srv/btbwebsite      0755 btbwebsite btbwebsite -"
    ];
}