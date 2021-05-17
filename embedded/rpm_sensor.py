"""
RPM sensor
"""

from collections import deque
import itertools
import time

import micropython
import pyb

from .inputs import Manager, Digital

# debugging
micropython.alloc_emergency_exception_buf(100)


# bookkeeping
pings_us = deque((), 12)
pings = deque((), 6)
prev_values = deque((), 3)
prev_values.extend(itertools.repeat((0, [], 0), 3))  # stock with base values


def ping_iq_on():
    pyb.LED(4).on()
    pings_us.append(time.ticks_us())
    pings.append(time.ticks_ms())


def ping_iq_off():
    pyb.LED(4).off()
    pings_us.append(time.ticks_us())


rpm_irq_mgr = Manager(
    [
        Digital("X8: hallsensor", hl_func=ping_iq_on, lh_func=ping_iq_off),
    ],
    timer_num=1,
    poll_freq=960,
)


def get_rpm(timeout=3.5, verbose=False):

    """
    Calculate RPMs by counting pings
    """

    # if zero pings, return 0
    if len(pings) == 0:
        prev_values.extend(itertools.repeat((0, [], 0), 3))
        rpm = 0
        us_diffs = []
        us_to_rpm_ratio = 0

    # if one ping, and previous values to use
    elif len(pings) == 1:

        # if prev values, use
        if len(prev_values) > 0:
            rpm, us_diffs, us_to_rpm_ratio = prev_values.popleft()

        # if none, assume stagnant for awhile; clear all
        else:
            prev_values.extend(itertools.repeat((0, [], 0), 3))
            pings_us.clear()
            pings.clear()
            rpm = 0
            us_diffs = []
            us_to_rpm_ratio = 0

    # else, calc new rpm
    else:
        # us_records
        us_diffs = []
        for x in range(0, 2):
            us_on = pings_us.popleft()
            us_off = pings_us.popleft()
            us_diffs.append(us_off - us_on)

        # rpm from microseconds
        ms_1 = pings.popleft()
        ms_2 = pings.popleft()
        rpm = 60 / ((ms_2 / 1000) - (ms_1 / 1000))

        # sensor time to rpm ratio
        us_to_rpm_ratio = sum(us_diffs) / rpm

        # override previous
        prev_values.extend(itertools.repeat((rpm, us_diffs, us_to_rpm_ratio), 3))

    # prepare response
    if verbose:
        return {"rpm": rpm, "us_diffs": us_diffs, "us_to_rpm_ratio": us_to_rpm_ratio}
    else:
        return {"rpm": rpm}
