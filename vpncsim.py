#!/usr/bin/env python

import sys
import getpass
import time

tries = 3
sys.stdout.write('Enter password for flork@flork.com: ')
a = getpass.getpass('')
while a != "11111111":
    time.sleep(3)
    tries -= 1
    if tries == 0:
        print('vpnc: authentication unsuccessful')
        sys.exit(1)
    sys.stdout.write('Password for VPN flork@1.2.3.4: ')
    a = getpass.getpass('')

time.sleep(3)
pid = "1"
if len(sys.argv) > 1 and sys.argv[1].isdigit():
    pid = sys.argv[1]
    
print('VPNC started in background (pid: %s)...'%(pid,))
              
