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
enable = pyb.Pin('X2')
tim = pyb.Timer(2, freq=1000)
ch = tim.channel(2, pyb.Timer.PWM, pin=enable)
in1 = pyb.Pin('X3', pyb.Pin.OUT_PP)
in2 = pyb.Pin('X4', pyb.Pin.OUT_PP)

# turn off
ch.pulse_width_percent(0)
in1.low()
in2.low()

# configs
lower_bound = 100
upper_bound = 3800
step = int((upper_bound - lower_bound) / 20)
print("Step increment: %s" % (step))


def ramp(start_power=0, end_power=50, steps=25, duration=2.0, dir='+'):

    """
    Function to smoothly apply and reduce power from start to end
    :return:
    """

    # p = int((ch.capture() / 84000) * 100)
    p = start_power
    for x in range(0, steps):
        if dir == '+':
            p += int(end_power / steps)
        else:
            p -= int(end_power / steps)
        ch.pulse_width_percent(p)
        time.sleep(duration/steps)
    return True


def sweep(duration=1, start_power=0, end_power=50, dir="+"):

    """
    Function to sweep for a specific duration and power level

    :param duration: length of time in seconds to move
    :param start: lower bound on power 
    """

    # start no power
    ch.pulse_width_percent(0)

    # set direction
    if dir == "+":
        in1.low()
        in2.high()
    else:
        in1.high()
        in2.low()

    # accelerate
    ramp(start_power=start_power, end_power=end_power, duration=(duration / 2), dir="+")

    # decelerate
    ramp(start_power=start_power, end_power=end_power, duration=(duration / 2), dir="-")

    # kill power and return
    ch.pulse_width_percent(0)
    return True


def move(steps, dir, start_power=0, end_power=50):

    """
    Function to apply a discrete number of small, smooth sweeps
    
    :param steps: number of sweeps
    :param dir: direction
        - "+": increase sensor position reading
        - "-": decrease sensor position reading
    :param power: power to 
    """

    for x in range(0, steps):
        sweep(duration=0.04, dir=dir, start_power=start_power, end_power=end_power)


def move_to_level_position(level):

    target = lower_bound + (level * step)
    prev_diff = 0
    loop_count = 0
    current = 0
    while True:
        loop_count += 1

        # read sensor with accuracy
        reads = 0
        num = 7
        accuracy = 0.04
        for x in range(0, num):
            reads += pos.read()
            time.sleep(accuracy / num)
        current = int(reads / num)
        diff = current - target
        # print("Target: %s, Current: %s, Prev Diff: %s, Diff: %s, Change: %s" % (target, current, prev_diff, diff, (prev_diff - diff)))
        prev_diff = diff

        # determine if settled
        if abs(diff) < 10:
            # print('settled!')
            break

        if abs(diff) > 1500:
            power = 100
        elif abs(diff) > 500:
            power = 80
        else:
            power = 50

        if current < target:
            move(5, dir="-", start_power=10, end_power=power)
        else:
            move(5, dir="+", start_power=10, end_power=power)

    # print("required loops: %s" % loop_count)
    return (level, target, current)


def rando():
    while True:
        move_to_level_position(random.randint(1,20))
        time.sleep(2)


def move_to_level_position_BAK(level):
    ch.pulse_width_percent(100)  # 9v @ 50% = 5.69v

    target = lower_bound + (level * step)

    prev_diff = 0
    loop_count = 0
    while True:

        loop_count += 1

        # triple beam
        reads = 0
        num = 10
        accuracy = 0.03
        for x in range(0,num):
            reads += pos.read()
            time.sleep(accuracy / num)
        current = int(reads/num)

        diff = current - target
        print("Target: %s, Current: %s, Prev Diff: %s, Diff: %s, Change: %s" % (target, current, prev_diff, diff, (prev_diff - diff)))
        prev_diff = diff

        # determine if settled
        if  abs(diff) < 10:
            in1.low()
            in2.low()
            print('settled!')
            break

        if current < target:
            in1.high()
            in2.low()
        else:
            in1.low()
            in2.high()

        time.sleep(0.002)
        in1.low()
        in2.low()

    print("required loops: %s" % loop_count)
    return True