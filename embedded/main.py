"""
TBOS: main embedded driver
"""

import json
import time

import pyb

from embedded.debug import repl_ping
from embedded.resistance_motor import read_position_sensor, goto_level, rm_status
from embedded.rpm_sensor import get_rpm


def status(lower_bound, upper_bound):

    """
    Return full sensor status
    """

    t0 = time.time()
    rm_reading = rm_status(lower_bound, upper_bound)
    rpm_reading = get_rpm(print_results=False)
    response = {"rm": rm_reading, "rpm": rpm_reading, "elapsed": time.time() - t0}
    print(json.dumps(response))
    return response
