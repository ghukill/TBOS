
import time

import serial

ser = serial.Serial('/dev/ttyACM0', 9600, timeout=1)

def msg(msg):
    ser.write((msg).encode('utf-8'))
    time.sleep(0.1)
    # TODO: add tries / timeout
    # QUESTION: replace with receieve for 1/2 second?        
    while True:
        response = ser.readline()
        if response != b'':            
            return response

def tester(s=0.0):
    for x in range(0,10):
        ser.write(("goober: %s" % str(x)).encode())
        time.sleep(s)
        r = ser.readline()
        print(r)