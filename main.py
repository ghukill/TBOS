# from controller.embedded import *

"""
Reading from serial...

import serial
ser = serial.Serial('/dev/ttyACM0', 9600, timeout=1)
ser.write(b'1')
"""

import time

import pyb

vcp = pyb.USB_VCP()
# vcp.setinterrupt(-1) # NOTE: might need if 3...

while True:
    time.sleep(1)
    data = vcp.readline()
    if data is not None:                
        vcp.write(("pyboard|%s\n" % data).encode('utf-8'))

