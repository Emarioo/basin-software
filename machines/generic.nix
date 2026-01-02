{ pkgs, ... }:
let
    hidden = import ./hidden.nix;
in
{
    services.openssh.enable = true;

    environment.systemPackages = with pkgs; [
        # essentials
        vim
        pkg-config
        wget
        curl
        unzip
        btop
        htop
        tmux
        git
        python311

        # extra
        mkpasswd

        # vscode
        nodePackages.nodejs
        ripgrep
        fd

        # programming tools
        # valgrind
        clang
        gcc13
        gdb
        cmake
        gnumake
        qemu
    ];

    programs.nix-ld.enable = true; # for remote-ssh node binary to work, # https://nixos.wiki/wiki/Visual_Studio_Code


    security.acme = {
        acceptTerms = true;
        defaults.email = hidden.acme_mail;
    };
    networking.firewall = {
        # enable = true;
        allowedTCPPorts = [
            80
            443
            22
        ];
    };
}