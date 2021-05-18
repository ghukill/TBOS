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
pings = deque((), 2)


def ping_iq_on():
    pyb.LED(4).on()
    pings.append(time.ticks_ms())


def ping_iq_off():
    pyb.LED(4).off()


rpm_irq_mgr = Manager(
    [
        Digital("X8: hallsensor", hl_func=ping_iq_on, lh_func=ping_iq_off),
    ],
    timer_num=1,
    poll_freq=480,
)


def get_rpm(verbose=False):

    """
    Calculate RPMs by counting pings
    """

    # if not enough pings, return immediately
    if len(pings) < 2:
        rpm = 0

    # else, calc rpm and return
    else:
        # rpm from microseconds
        ms_1 = pings.popleft()
        ms_2 = pings.popleft()
        rpm = 60 / ((ms_2 / 1000) - (ms_1 / 1000))

    # prepare response
    if verbose:
        return {"rpm": rpm}
    else:
        return {"rpm": rpm}
