#!/usr/bin/env python

# wmvpnc - a dockapp frontend for vpnc
# Copyright (C) 2019 Johannes Holmberg, johannes@update.uu.se
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import sys
import time
import getopt
import os
import subprocess
import threading

import pexpect
import wmdocklib

VERSION = '0.1'

cfg = None
default_cfg_filename = '~/.config/wmvpnc/wmvpncrc'

areas = []
i = 0
for y in range(4):
    for x in range(3):
        areas.append((i, 4 + 13*x, 16 + 11*y, 12, 10))
        i += 1

areas.append((12, 43, 16, 17, 21))
areas.append((13, 43, 38, 17, 21))

usage = """Usage: wmvpnc.py [OPTION]...

Options:
-c, --config-file FILE           set the config file to use
-m, --mask-password              mask the password
-p, --password-length N          automatically send password after N characters
-t, --token-command C            command line to get a token
-n, --token-pin                  token generator requires a pin
-v, --vpnc-command C             command line to use for connecting
-d, --vpnc-disconnect-command C  command line to use for disconnecting
-a, --vpn-died-alarm-command C   command line to generate alarm when vpn dies
-r, --vpn-died-reset-command C   command line to silence above alarm
--debug                          print debug stuff
--help                           display this help and exit
--version                        display version information and exit
"""

def debug(str):
    if cfg.get('debug'):
        print(str)

def blink(cursor_position, counter):
    if cursor_position <= 8:
        if counter & 3 == 0:
            if counter & 4:
                wmdocklib.copyXPMArea(168, 77, 6, 9, 4 + 6*cursor_position, 5)
            else:
                wmdocklib.copyXPMArea(174, 77, 6, 9, 4 + 6*cursor_position, 5)

def spinner(counter):
    i = counter & 3
    wmdocklib.copyXPMArea(80 + 6*i, 67, 6, 9, 4, 5)

def cls():
    wmdocklib.copyXPMArea(0, 87, 54, 9, 4, 5)

def putc(c, x, y):
    a = ord(c)
    if ord('A') <= a <= ord('Z'):
        sy = 77
        sx = (a - 65) * 6
    elif ord('0') <= a <= ord('9'):
        sy = 67
        sx = (a - 48) * 6
    elif c == ' ':
        sy = 67
        sx = 66
    wmdocklib.copyXPMArea(sx, sy, 6, 9, x, y)

def printf(msg):
    cls()
    i = 4
    for c in msg:
        putc(c, i, 5)
        i += 6

def press(region):
    wmdocklib.copyXPMArea(128 + areas[region][1],
                          areas[region][2],
                          areas[region][3],
                          areas[region][4],
                          areas[region][1],
                          areas[region][2])

def release(region):
    wmdocklib.copyXPMArea(64 + areas[region][1],
                          areas[region][2],
                          areas[region][3],
                          areas[region][4],
                          areas[region][1],
                          areas[region][2])


# vpnc monitor thread states
VPNC_STARTED = 0
VPNC_ENTER_PASSWORD = 1
VPNC_RETRY_PASSWORD = 2
VPNC_UP = 3
VPNC_FAILED = 4
VPNC_AUTH_FAILED = 5
VPNC_DISCONNECTING = 6
VPNC_DISCONNECTED = 7
VPNC_DIED = 8

# control = [vpnc_state, password, disconnect, error_msg]
def vpnc_connect(control):
    debug('vpnc: ' + str(control))
    p = pexpect.spawn(cfg['vpnc-command'], timeout=120)
    control[0] = VPNC_STARTED
    debug('vpnc: spawned')
    a = p.expect(['Enter password for.*:', pexpect.EOF])
    if a == 1:
        debug('vpnc: vpnc failed')
        control[0] = VPNC_FAILED
        return

    control[0] = VPNC_ENTER_PASSWORD

    while True:
        while control[1] is None:
            time.sleep(0.5)
        debug('vpnc: sending password: ' + str(control[1]))
        p.sendline(control[1])
        a = p.expect(['VPNC started in background \(pid: (\\d*)\)', 'Password for.*:', 'vpnc: authentication unsuccessful', 'vpnc: .*', pexpect.TIMEOUT])
        if a == 0:
            pid = p.match.group(1)
            p.expect(pexpect.EOF)
            debug('vpnc: vpn up, pid %s'%(pid,))
            control[0] = VPNC_UP
            break
        elif a == 1:
            debug('vpnc: bad password')
            control[0] = VPNC_RETRY_PASSWORD
            control[1] = None
        elif a == 2:
            debug('vpnc: auth failed')
            control[0] = VPNC_AUTH_FAILED
            return
        elif a == 3:
            debug('vpnc: unknown but bad result')
            error = p.match.string[p.match.string.index('vpnc: ') + 6:]
            debug('vpnc output: ' + error)
            control[3] = error
            control[0] = VPNC_FAILED
            return
        elif a == 4:
            debug('vpnc timeout')
            p.close()
            control[3] = "timeout"
            control[0] = VPNC_FAILED
            return

    # Monitor pid
    pidpath = '/proc/' + pid
    while True:
        time.sleep(2)
        if not os.path.isdir(pidpath):
            control[0] = VPNC_DIED
            return
        if control[2]:
            debug('vpnc: disconnect requested')
            control[0] = VPNC_DISCONNECTING
            p = pexpect.spawn(cfg['vpnc-disconnect-command'])
            p.expect(['Terminating vpnc daemon','no vpnc found running'])
            p.expect(pexpect.EOF)
            control[0] = VPNC_DISCONNECTED
            return

def cfg_token_with_pin():
    return 'token-pin' in cfg and 'token-command' in cfg

def cfg_token_without_pin():
    if 'token-command' in cfg:
        if 'token-pin' not in cfg or not cfg['token-pin']:
            return True

def get_token(password=None):
    p = pexpect.spawn(cfg['token-command'], echo=False)
    if password:
        p.sendline(password)
    p.expect(pexpect.EOF)
    pw = p.before.strip().split('\n')[-1]
    debug('token: ' + pw)
    return pw

def vpn_died_alarm():
    if 'vpn-died-alarm-command' in cfg:
        debug("vpn died, running alarm cmd")
        subprocess.Popen(cfg['vpn-died-alarm-command'], shell=True)

def vpn_died_reset():
    if 'vpn-died-reset-command' in cfg:
        debug("vpn death acknowledged")
        subprocess.Popen(cfg['vpn-died-reset-command'], shell=True)

# Main program states
START = 0
RUN_VPNC = 1
ENTER_PIN = 2 # Nothing entered yet
ENTERING_PIN = 3 # Screen cleared
RETRY_PIN = 4
WAIT_VPNC_CONNECT = 5
VPN_UP = 6
WAIT_VPNC_SHUTDOWN = 7
VPN_DIED = 8

def mainLoop():
    ui_speedup = 0
    state = START
    pressed = None
    cursor_position = 0
    blinking = True
    counter = 0
    code = []
    event = None
    vpnc_state = [None, None, False]
    password_length = cfg.get('password-length')
    if password_length is not None:
        password_length = int(password_length) if password_length.isdigit() else None

    while 1:
        if ui_speedup > 0:
            time.sleep(0.05)
            if ui_speedup & 1 == 1:
                counter += 1
            ui_speedup -= 1
        else:
            time.sleep(0.1)
            counter += 1

        if event is None:
            event = wmdocklib.getEvent()
        if event is not None:
            if event['type'] == 'buttonpress' and event['button'] == 1:
                    region = wmdocklib.checkMouseRegion(event['x'], event['y'])
                    if region >= 0:
                        pressed = region
                        press(region)
                        ui_speedup = 2 + (ui_speedup & 1)
            elif event['type'] == 'buttonrelease' and event['button'] == 1:
                if pressed is not None:
                    release(pressed)
                    region = wmdocklib.checkMouseRegion(event['x'], event['y'])
                    if pressed == region: # A button was pressed, do something
                        if pressed == 9:
                            if cursor_position > 0:
                                if cursor_position <= 9:
                                    wmdocklib.copyXPMArea(174, 77, 6, 9, 4 + 6*(cursor_position - 1), 5)
                                    if cursor_position <= 8:
                                        wmdocklib.copyXPMArea(174, 77, 6, 9, 4 + 6*cursor_position, 5)
                                cursor_position -= 1
                                code.pop()

                        elif pressed < 11:
                            if state == ENTER_PIN:
                                cls()
                                state = ENTERING_PIN

                            if state == ENTERING_PIN:
                                if pressed == 10:
                                    c = 0
                                else:
                                    c = pressed + 1
                                code.append(c)
                                counter = 4 # Cheap trick to get cursor to show right away
                                if cursor_position <= 8:
                                    if cfg.get('mask-password'):
                                        wmdocklib.copyXPMArea(162, 77, 6, 9, 4 + 6*cursor_position, 5)
                                    else:
                                        putc(str(c), 4 + 6*cursor_position, 5)
                                cursor_position += 1

                        if pressed == 11 or len(code) == password_length: # PIN entered
                            if state == ENTERING_PIN:
                                password = ''.join([str(x) for x in code])
                                debug('Entered pin: ' + password)
                                if cfg_token_with_pin():
                                    password = get_token(password)
                                state = WAIT_VPNC_CONNECT
                                vpnc_state[1] = password
                                vpnc_state[0] = VPNC_ENTER_PASSWORD # Inconsiderate!
                                code = []
                                cursor_position = 0
                                cls()

                        if pressed == 12: # Connect
                            if state == VPN_DIED:
                                cls()
                                vpn_died_reset()
                                state = START
                            if state == START:
                                state = RUN_VPNC
                                vpnc_state = [None, None, False, None]
                                thread = threading.Thread(target=vpnc_connect, args = (vpnc_state,))
                                thread.setDaemon(True)
                                thread.start()
                                cursor_position = 0

                        elif pressed == 13: # Disconnect
                            if state == VPN_UP:
                                cls()
                                state = WAIT_VPNC_SHUTDOWN
                                vpnc_state[2] = True
                            elif state == VPN_DIED:
                                cls()
                                vpn_died_reset()
                                state = START

                pressed = None
            elif event['type'] == 'destroynotify':
                sys.exit(0)
            event = None

        wmdocklib.redraw()

        # Animations and polling
        if state == ENTERING_PIN:
            blink(cursor_position, counter)

        if state == RUN_VPNC:
            if vpnc_state[0] == VPNC_ENTER_PASSWORD:
                if cfg_token_without_pin():
                    password = get_token()
                    state = WAIT_VPNC_CONNECT
                    vpnc_state[1] = password
                    vpnc_state[0] = VPNC_ENTER_PASSWORD # Inconsiderate!
                else:
                    printf('ENTER PIN')
                    state = ENTER_PIN
            elif vpnc_state[0] == VPNC_FAILED:
                printf('FAILURE')
                state = START

        if state == WAIT_VPNC_CONNECT:
            spinner(counter)
            if vpnc_state[0] == VPNC_UP:
                printf('CONNECTED')
                state = VPN_UP
            elif vpnc_state[0] == VPNC_FAILED:
                printf('FAILURE')
                state = START
            elif vpnc_state[0] == VPNC_RETRY_PASSWORD:
                if cfg_token_without_pin():
                    password = get_token()
                    state = WAIT_VPNC_CONNECT
                    vpnc_state[1] = password
                    vpnc_state[0] = VPNC_ENTER_PASSWORD # Inconsiderate!
                else:
                    printf('TRY AGAIN')
                    state = ENTER_PIN
            elif vpnc_state[0] == VPNC_AUTH_FAILED:
                printf('AUTH FAIL')
                state = START

        if state == WAIT_VPNC_SHUTDOWN:
            spinner(counter)
            if vpnc_state[0] == VPNC_DISCONNECTED:
                printf('VPN OFF')
                state = START

        if state == VPN_UP or state == WAIT_VPNC_CONNECT:
            if vpnc_state[0] == VPNC_DIED:
                printf('VPN DIED')
                vpn_died_alarm()
                state = VPN_DIED

def parse_options(argv):
    shorts = 'a:c:d:mnp:r:t:v:'
    longs = ['debug', 'configfile=', 'help', 'mask-password', 'password-length=',
             'token-command=', 'token-pin', 'vpnc-command=',
             'vpnc-disconnect-command=', 'version',
             'vpn-died-alarm-command=', 'vpn-died-reset-command=']
    try:
        opts, other_args = getopt.getopt(argv[1:], shorts, longs)
    except getopt.GetoptError, e:
        sys.stderr.write('Faile to parse command line: ' + str(e) + '\n')
        sys.stderr.write(usage + '\n')
        sys.exit(2)

    d = {}
    for o, a in opts:
        if o in ('-c', '--config-file'):
            d['config-file'] = a
        elif o in ('--debug',):
            d['debug'] = True
        elif o in ('-t', '--token-command'):
            d['token-command'] = a
        elif o in ('-n', '--token-pin',):
            d['token-pin'] = True
        elif o in ('-d', '--vpnc-disconnect-command'):
            d['vpnc-disconnect-command'] = a
        elif o in ('--help',):
            print(usage)
            sys.exit(0)
        elif o in ('-m', '--mask-password'):
            d['mask-password'] = True
        elif o in ('-p', '--password-length'):
            d['password-length'] = a
        elif o in ('--version',):
            print('wmvpnc ' + VERSION)
            sys.exit(0)
        elif o in ('-v', '--vpnc-command'):
            d['vpnc-command'] = a
        elif o in ('-a', '--vpn-died-alarm-command'):
            d['vpn-died-alarm-command'] = a
        elif o in ('-r', '--vpn-died-reset-command'):
            d['vpn-died-reset-command'] = a
    return d

def main():
    global cfg
    opts = parse_options(sys.argv)
    cfg_filename = opts.get('config-file', default_cfg_filename)
    cfg_filename = os.path.expanduser(cfg_filename)
    cfg = wmdocklib.readConfigFile(cfg_filename, sys.stderr)

    # Override config file with command line options
    for i in opts.iteritems():
        cfg[i[0]] = i[1]

    try:
        programName = sys.argv[0].split(os.sep)[-1]
    except IndexError:
        programName = ''
    sys.argv[0] = programName

    pal, pxl = wmdocklib.readXPM("wmvpnc.xpm")
    wmdocklib.initPixmap(patterns=None, palette=pal, background=pxl)

    wmdocklib.openXwindow(sys.argv, 64, 64)
    for area in areas:
        wmdocklib.addMouseRegion(area[0], area[1], area[2], width=area[3], height=area[4])
    mainLoop()

if __name__ == '__main__':
    main()
