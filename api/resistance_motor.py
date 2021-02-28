"""
Main host driver of embedded code

TODO: move to clients
"""

import random
import time

import serial

import pyboard

try:
    pyb = pyboard.Pyboard("/dev/ttyACM0", 115200)
except:
    print("WARNING: cannot access pyboard")
    pyb = None


def direct_move(level):

    """"""

    if pyb is not None:
        pyb.enter_raw_repl()
        pyb.exec("from controller.embedded import move_to_level_position")
        pyb.exec(f"move_to_level_position({level})")
        pyb.exit_raw_repl()
        return level
    else:
        time.sleep(2)
        return level
