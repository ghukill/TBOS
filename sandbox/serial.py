"""
Sandboxing serial comms
"""

import time

import serial

ser = serial.Serial("/dev/ttyACM0", 9600, timeout=1)
print(ser.readlines())
ser.flush()


def msg(msg):
    ser.write((msg).encode("utf-8"))
    time.sleep(0.1)
    # TODO: add tries / timeout
    # QUESTION: replace with receive for 1/2 second?
    while True:
        response = ser.readline()
        if response != b"":
            return response
