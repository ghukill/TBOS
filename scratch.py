"""
Serial testing
"""

import time

import pyb

vcp = pyb.USB_VCP()
# vcp.setinterrupt(-1) # NOTE: might need if 3...

while True:
    pyb.delay(200) # listen delay
    if vcp.any() > 0:
        pyb.delay(100) # know data coming, wait for complete
        data = vcp.readline()
        vcp.write(b'pyboard copy')
        pyb.delay(200) # wait for pi to gobble

