"""
TBOS: main embedded driver
"""

import json

import pyb

from embedded.debug import repl_ping
from embedded.resistance_motor import read_position_sensor, goto_level, rm_status
from embedded.rpm_sensor import get_rpm


def status(lower_bound, upper_bound):

    """
    Return full sensor status
    """

    return {"rm": rm_status(lower_bound, upper_bound), "rpm": get_rpm()}
