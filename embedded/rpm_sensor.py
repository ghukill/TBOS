"""
RPM sensor

TODO
    - possible improvement, record time diff between last two pings (stored in 2nd queue)
"""

from collections import deque
import time

import micropython

micropython.alloc_emergency_exception_buf(100)

from .inputs import Manager, Digital


# bookkeeping
pings = deque((), 480)


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


def get_rpm(sample_size=10, debug=False):

    """
    Calculate RPMs by counting pings
    TODO: prune pings sometimes...
    """

    current_second = int(time.time())

    # copy pings to local instance
    # NOTE: possible shuffle if incoming, but that's okay
    # print("BEFORE length of pings: %s" % len(pings))
    _pings = []
    while len(pings) > 0:
        _pings.append(pings.popleft())
    for ping in _pings:
        pings.append(ping)
    # print("AFTER length of pings: %s" % len(pings))

    # if not pings, return 0
    if len(_pings) == 0:
        return 0.0

    # reduce to sample size
    sample_pings = []
    while len(_pings) > 0:
        ping = _pings.pop()
        if (current_second - ping) >= sample_size:
            # print("breaking because ping is too old...")
            break
        else:
            sample_pings.append(ping)

    # math it up and return
    # print("length sample pings: %s" % len(sample_pings))
    rpm = (len(sample_pings) / sample_size) * 60
    print(rpm)
    return rpm
