# wmvpnc

## Prerequisites

wmvpnc requires wmdocklib and pexpect.

## Configuration

By default, wmvpnc looks for a configuration file in
~/.config/wmvpnc/wmvpncrc.
The most important setting is vpnc-connect which is the command line
to use for connecting to your vpn. Typically this will be something
like "/usr/sbin/vpnc myvpn", but it could also be a shell script that
runs vpnc and then does some additional stuff, perhaps adding or
removing routes. There are two requirements on such a script:
1. Any output from vpnc must remain intact (i.e., not be suppressed
or redirected)
2. The script must terminate (more or less shortly) after the vpn
connection has been made

vpnc-disconnect-command will typically be /usr/sbin/vpnc-disconnect,
but again, a script will work and the same rules as above apply.

## Connecting and disconnecting

Press the green button to initiate a new connection. If vpnc-command
is configured properly you will be asked for your password (ENTER
PIN). Enter your password and hopefully you will be connected to your
vpn. Press the red button to disconnect.

## Hacking

Using vpncsim.py as your vpnc-command when developing is recommended
in order to avoid unnecessary connecting and disconnecting from your
vpn.
