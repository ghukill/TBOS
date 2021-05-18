"""
RPM sensor
"""

from collections import deque
import time

import micropython
import pyb

from .inputs import Manager, Digital

# debugging
micropython.alloc_emergency_exception_buf(100)


# bookkeeping
pings = deque((), 6)
prev_values_num = 3
prev_values = deque((), prev_values_num)


def set_prev_values(repeat_val):
    """
    Update stack of previous values
    """
    for x in range(0, prev_values_num):
        prev_values.append(repeat_val)


set_prev_values(0)  # stock with base zeros


def ping_iq_on():
    pyb.LED(4).on()
    pings.append(time.ticks_ms())


def ping_iq_off():
    pyb.LED(4).off()


def clear_queue(d):
    while True:
        try:
            _ = d.popleft()
        except:
            break


rpm_irq_mgr = Manager(
    [
        Digital("X8: hallsensor", hl_func=ping_iq_on, lh_func=ping_iq_off),
    ],
    timer_num=1,
    poll_freq=960,
)


def get_rpm(verbose=False):

    """
    Calculate RPMs by counting pings
    """

    # if zero pings, return 0
    if len(pings) == 0:
        set_prev_values(0)
        rpm = 0
        us_diffs = []
        us_to_rpm_ratio = 0

    # if one ping, and previous values to use
    elif len(pings) == 1:

        # if prev values, use
        if len(prev_values) > 0:
            rpm = prev_values.popleft()

        # if none, assume stagnant for awhile; clear all
        else:
            set_prev_values(0)
            clear_queue(pings)
            rpm = 0
            us_diffs = []
            us_to_rpm_ratio = 0

    # else, calc new rpm
    else:
        # rpm from microseconds
        ms_1 = pings.popleft()
        ms_2 = pings.popleft()
        rpm = 60 / ((ms_2 / 1000) - (ms_1 / 1000))

        # override previous
        set_prev_values(rpm)

    # prepare response
    if verbose:
        return {"rpm": rpm, "us_diffs": us_diffs, "us_to_rpm_ratio": us_to_rpm_ratio}
    else:
        return {"rpm": rpm}
