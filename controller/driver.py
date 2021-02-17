"""
Drive arduino adjuster
"""

import random
import time

import serial


ser = serial.Serial("/dev/ttyACM0", 9600, timeout=1)
ser.flush()

ser.write("c".encode("utf-8"))

new_value_okay = True

while True:

    if int(time.time()) % 5 == 0:
        values = ["+", "-"]
        new_value = values[random.randint(0,len(values)-1)]
        if new_value_okay:
            print(f"writing new value: {new_value}")
            ser.write(new_value.encode("utf-8"))
            new_value_okay = False
    else:
        new_value_okay = True

    if ser.in_waiting > 0:
        line = ser.readline().decode("utf-8").rstrip()
        print(line)
