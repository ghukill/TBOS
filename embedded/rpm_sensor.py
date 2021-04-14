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


def get_rpm(timeout=3.5, verbose=False):

    """
    Calculate RPMs by counting pings
    """

    # bookkeeping
    pings_us = deque((), 4)
    pings = deque((), 2)

    def ping_iq_on():
        pings_us.append(time.ticks_us())
        pings.append(time.ticks_ms())

    def ping_iq_off():
        pings_us.append(time.ticks_us())

    mgr = Manager(
        [
            Digital("X8: hallsensor", hl_func=ping_iq_on, lh_func=ping_iq_off),
        ],
        timer_num=1,
        poll_freq=960,
    )

    t0 = time.time()
    while len(pings_us) < 4:
        if time.time() - t0 > timeout:
            break
        else:
            continue

    if len(pings_us) >= 4:

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

    else:
        us_diffs = []
        rpm = 0
        us_to_rpm_ratio = 0

    # prepare response
    if verbose:
        return {"rpm": rpm, "us_diffs": us_diffs, "us_to_rpm_ratio": us_to_rpm_ratio}
    else:
        return {"rpm": rpm}
