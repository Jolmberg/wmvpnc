#!/usr/bin/env python

import sys

if '--token-pin' in sys.argv:
    pwd = sys.stdin.readline().strip()
    if pwd.replace('9','') == '':
        print('11111111')
    else:
        print('12345678')
else:
    if '--correct' in sys.argv:
        print('11111111')
    else:
        print('12345678')
