A little about how the routing files work.

Our infrastructure is broken down into machines and services.

Machines have ip addresses.

Each service exist on one of the machines.

Some example services are:
- git with web interface
- ender compute with web interface (tests and builds)
- Game servers

These services have a subdomain each.

The relations and ports,subdomains the services and machines
are declared in nix files and out comes:
- actions to transfer services between machines or start them if they don't exist
- config for reverse proxy on each machine to route subdomain to correct port where service lives at.


The purpose of this system is to automatically move services and configure the settings for each machine
so a developer doesn't have to spend a data tweaking it. Also, if some servers shutsdown or
is lost then you can easily start them up again using this sytem. You may still need to do
some ssh to fix some things or complicated problems but most of the time it should be a convenient system.

It would be easy if each service had it's own machine but machines are expensive, most services
can share machines.

Each service has a subdomain and ports. git.company.org:22 and git.company.org:443.
Externally multiple services on one machine has https but internally they map to different ports
using reverse proxy service.



We don't use docker because it's unnecessary. more fluffy abstractions is bad.

