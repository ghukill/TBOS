
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


def g1(level):
    ch.pulse_width_percent(50)  # 9v @ 50% = 5.69v

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


def ramp(start=0, power=50, steps=25, duration=2.0, dir='+'):

    """
    Function to bring motor up to speed in 0.25s
    :return:
    """

    # p = int((ch.capture() / 84000) * 100)
    p = start
    for x in range(0, steps):
        if dir == '+':
            p += int(power / steps)
        else:
            p -= int(power / steps)
        ch.pulse_width_percent(p)
        time.sleep(duration/steps)
    return True


def sweep(duration=1, start=0, power=50, dir="+"):

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
    ramp(start=start, target=power, duration=(duration / 2), dir="+")

    # decelerate
    ramp(start=power, target=power, duration=(duration / 2), dir="-")

    ch.pulse_width_percent(0)
    return True


def move(steps, dir, power=50):
    for x in range(0, steps):
        sweep(duration=0.04, dir=dir, power=power)


def g2(level):

    target = lower_bound + (level * step)
    prev_diff = 0
    loop_count = 0
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
        print("Target: %s, Current: %s, Prev Diff: %s, Diff: %s, Change: %s" % (
        target, current, prev_diff, diff, (prev_diff - diff)))
        prev_diff = diff

        # determine if settled
        if abs(diff) < 10:
            print('settled!')
            break

        if abs(diff) > 1500:
            power = 100
        elif abs(diff) > 500:
            power = 80
        else:
            power = 50

        if current < target:
            move(5, dir="-", power=power)
        else:
            move(5, dir="+", power=power)

    print("required loops: %s" % loop_count)
    return True


def rando():
    while True:
        g2(random.randint(1,20))
        time.sleep(2)
