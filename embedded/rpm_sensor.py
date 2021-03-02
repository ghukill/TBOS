"""
RPM sensor

TODO
    - possible improvement, record time diff between last two pings (stored in 2nd queue)
"""

from collections import deque
import json
import time

import micropython
import pyb

from .inputs import Manager, Digital

# debugging
micropython.alloc_emergency_exception_buf(100)

# bookkeeping
pings = deque((), 120)


# setup interrupt manager
def ping_iq():
    pings.append(int(time.time()))


mgr = Manager(
    [
        Digital("X8: hallsensor", hl_func=ping_iq),
    ],
    timer_num=1,
    poll_freq=480,
)


def get_rpm(sample_size=5, debug=False):

    """
    Calculate RPMs by counting pings
    """

    # delay for sample size duration to allow manager interrupts
    pyb.delay(sample_size * 1000)

    # after delay, get second to move backwards from
    current_second = int(time.time())

    # copy pings to local instance
    _pings = []
    while len(pings) > 0:
        _pings.append(pings.popleft())
    for ping in _pings:
        pings.append(ping)

    # if not pings, return 0
    if len(_pings) == 0:
        rpm = 0.0

    else:
        # reduce to sample size
        sample_pings = []
        while len(_pings) > 0:
            ping = _pings.pop()
            if (current_second - ping) >= sample_size:
                break
            else:
                sample_pings.append(ping)

        # project to RPMs
        rpm = (len(sample_pings) / sample_size) * 60

    # prepare response
    response = {"rpm": rpm, "sample_size": sample_size, "num_sample_pings": len(sample_pings)}
    print(json.dumps(response))
    return response
