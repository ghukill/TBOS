"""
Code for embedded TBOS functionality:
    - resistance motor control
    - speed sensor
    - power management
"""

import random
import time

import pyb

# define pins
pos = pyb.ADC(0)
enable = pyb.Pin("X2")
tim = pyb.Timer(2, freq=1000)
ch = tim.channel(2, pyb.Timer.PWM, pin=enable)
in1 = pyb.Pin("X3", pyb.Pin.OUT_PP)
in2 = pyb.Pin("X4", pyb.Pin.OUT_PP)

# turn off
ch.pulse_width_percent(0)
in1.low()
in2.low()

# motor configurations
# TODO: update for real motor
lower_bound = 100
upper_bound = 3800
step = int((upper_bound - lower_bound) / 20)
settled_threshold = 30


def read_position_sensor(num_reads=5, read_delay=0.05):

    """
    Sample sensor value multiple times rapidly, average, and return
    """

    reads = []
    for x in range(0, num_reads):
        reads.append(pos.read())
        time.sleep(read_delay / num_reads)
    current = sum(reads) / num_reads
    return current


def goto_level(level, pwm_level=75, debug=False):

    """
    :param pwm_level: percentage of input 9v
        - 9v @ 50% = 5.69v

    TODO:
        - output loops and avg distance of loop iteration
    """

    target = lower_bound + (level * step)

    prev_diff = 0
    loop_count = 0
    while True:

        loop_count += 1

        # get sensor value
        current = read_position_sensor()

        diff = current - target
        if debug:
            print(
                "Target: %s, Current: %s, Prev Diff: %s, Diff: %s, Change: %s"
                % (target, current, prev_diff, diff, (prev_diff - diff))
            )
        prev_diff = diff

        # determine if settled
        if abs(diff) < settled_threshold:
            ch.pulse_width_percent(0)
            in1.low()
            in2.low()
            if debug:
                print("settled")
            break

        else:
            ch.pulse_width_percent(pwm_level)

            if current < target:
                in1.high()
                in2.low()
            else:
                in1.low()
                in2.high()

            time.sleep(0.003)
            in1.low()
            in2.low()

    if debug:
        print("required loops: %s" % loop_count)
    return True
