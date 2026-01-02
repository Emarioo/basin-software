{ lib, ... }:

let
  machines = {
    primary          = { domain = "basin-software.org"; ip = "203.0.113.10"; };
    backup           = { domain = "basin-software.org"; ip = "198.51.100.5"; };
    odingame_server0 = { domain = "odingame.org";       ip = "198.51.100.29"; };
  };

  services = {

    ##################################
    #    internal company services
    ##################################
    git = {
      host = "git.basin-software.org";
      portmap = {   "80"  = "3000";
                    "443" = "3001"; };
    };

    ender = {
      host = "ender.basin-software.org";
      portmap = {   "80"  = "3010";
                    "443" = "3011"; };
    };

    #############################
    #    public web services
    #############################
    wanderer_website = {
      host = "wanderer.basin-software.org";
      portmap = {   "80"  = "3020";
                    "443" = "3021"; };
    };

    odingame_website = {
      host = "odingame.org";
      portmap = {   "80"  = "3100";
                    "443" = "3101"; };
    };

    ##############################
    #    public game services
    ##############################
    wanderer_public_server = {
      host = "wanderer-serv0.basin-software.org";
      portmap = {   "4000"  = "4000"; };
    };

    odingame_public_server = {
      host = "serv0.odingame.org";
      portmap = {   "4100"  = "4100"; };
    };

  };
in
{
  inherit machines services;
}
