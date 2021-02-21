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
    data = vcp.read()
    if data is not None:
        vcp.write(data)
    time.sleep(.5)


