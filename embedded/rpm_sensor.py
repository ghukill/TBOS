"""
RPM sensor
"""

from collections import deque
import json
import time

import micropython
import pyb

from .inputs import Manager, Digital

# debugging
micropython.alloc_emergency_exception_buf(100)

# pins
ping_led = pyb.LED(4)
_blink_led = False

# bookkeeping
pings_us = deque((), 4)
pings = deque((), 2)


def ping_iq_on():
    pings_us.append(time.ticks_us())
    pings.append(time.ticks_ms())
    if _blink_led:
        ping_led.on()


def ping_iq_off():
    pings_us.append(time.ticks_us())
    if _blink_led:
        ping_led.off()


mgr = Manager(
    [
        Digital("X8: hallsensor", hl_func=ping_iq_on, lh_func=ping_iq_off),
    ],
    timer_num=1,
    poll_freq=480,
)


def get_rpm(timeout=3.5, blink_led=False, print_results=True):

    """
    Calculate RPMs by counting pings
    """

    # update blink flag
    _blink_led = blink_led

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
    response = {"rpm": rpm, "us_diffs": us_diffs, "us_to_rpm_ratio": us_to_rpm_ratio}
    if print_results:
        print(json.dumps(response))
    return response
