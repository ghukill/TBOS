"""
Main host driver of embedded code
"""

import random
import time

import serial

import pyboard
pyb = pyboard.Pyboard('/dev/ttyACM0', 115200)

ser = serial.Serial("/dev/ttyACM0", 9600, timeout=1)
print(ser.readlines())
ser.flush()


def msg(msg):
    ser.write((msg).encode('utf-8'))
    time.sleep(0.1)
    # TODO: add tries / timeout
    # QUESTION: replace with receieve for 1/2 second?        
    while True:
        response = ser.readline()
        if response != b'':            
            return response

def direct_move(level):
    pyb.enter_raw_repl()
    pyb.exec('from controller.embedded import move_to_level_position')
    pyb.exec(f'move_to_level_position({level})')
    pyb.exit_raw_repl()
    print('finis')