# wmvpnc

## Prerequisites

wmvpnc requires wmdocklib and pexpect.

## Configuration

By default, wmvpnc looks for a configuration file in
~/.config/wmvpnc/wmvpncrc.
Most command line options can also be configured in the configuration
file. Run wmvpnc.py --help to see the full list. If an option is
present in the configuration file as well as on the command line, the
value given on the command line will take precedence.

The most important setting is vpnc-connect which is the command line
to use for connecting to your VPN. Typically this will be something
like "/usr/sbin/vpnc myvpn", but it could also be a shell script that
runs vpnc and then does some additional stuff, perhaps adding or
removing routes. There are two requirements on such a script:
1. Any output from vpnc must remain intact (i.e., not be suppressed
or redirected)
2. The script must terminate (more or less shortly) after the VPN
connection has been made

vpnc-disconnect-command will typically be /usr/sbin/vpnc-disconnect,
but again, a script will work and the same rules as above apply.

## Connecting and disconnecting

Press the green button to initiate a new connection. If vpnc-command
is configured properly you will be asked for your password (ENTER
PIN). Enter your password and hopefully you will be connected to your
VPN. Press the red button to disconnect.

## Using a token generator

If you use a software token generator to connect to your VPN, you
might be able to interface with it using the --token-command option
(or configuration parameter). The token-command can be any executable
or script, the only requirement on it is that it prints the VPN
password as its last line of output.

If your token generator requires a pin code you can add the flag
--token-pin and you will be asked to punch in the pin code on the
dockapp keypad. The pin code followed by a newline will be written to
the stdin of your token-command program immediately after it
launches. Most likely you will need to wrap your token generator in a
script to get this to work.

## Non-numeric passwords

If your vpn password contains non-numeric characters, the dockapp
keypad obviously won't do. A trick to get around this is to use
the --token-command option to trigger a simple password reader, eg
--token-command "zenity --password".

The same strategy can be used if you use a real token generator that
requires a non-numeric pin code. Skip the --token-pin option and
instead wrap your token generator in a script that begins by
requesting the pin through zenity. Obviously, if you have come this
far, you could just hard-code your token pin in the wrapper script
for a blissful one-click connect but I will leave it to you to
consider the security implications of doing so. :)

## Alarms

Once a VPN connection is established, wmvpnc monitors the pid of the
vpnc process. If the vpnc process dies unexpectedly, wmvpnc will
display the string "VPN DIED". As this might not be enough to attract
your attention you can use the option --vpn-died-alarm-command to
supply a command line to be run when the VPN dies. wmvpnc does not
wait for this command to terminate and it does not care about its
output. Depending on what your alarm command does, you may want to
run a separate command to undo it once you have noticed that the VPN
is down. This can be configured with the --vpn-died-reset-command.
As with the alarm command, wmvpnc does not care what this command
does. When the VPN has died, press the disconnect button or the
connect button to acknowledge the failure and run the reset command.

A silly example of how to use these options:
```
--vpn-died-alarm-command "xsetroot -solid '#ff0000'"
--vpn-died-reset-command "xsetroot -solid '#000000'"
```

## Hacking

Using vpncsim.py as your vpnc-command when developing is recommended
in order to avoid unnecessary connecting and disconnecting from your
VPN. vpncsim.py can produce all of the output strings of vpnc that
wmvpnc considers interesting. Use the password 11111111 to simulate
a successful login, and any other password to simulate a failed one.
Optionally you can supply a number on the command line to use as the
pid returned after a successful login. This is useful to test the VPN
monitoring aspect of wmvpnc.

tokensim.py can be used as a simple token generator. For password-
less token generation run it with no flags to generate an incorrect
token (12345678) or with the flag --correct to get the correct
token (11111111). To simulate a token generator requiring a pin code,
run it with the --token-pin flag. Any pin containing zero or more
9s is considered correct and will yield the 11111111 password
Anything else will result in 12345678.

Use the --debug flag to get some helpful printouts during execution.
But do note that any password you enter will be visible in the
printouts.
