"""
TBOS: main embedded driver
"""

import json

import pyb

from embedded.debug import repl_ping
from embedded.resistance_motor import read_position_sensor, goto_level
from embedded.rpm_sensor import get_rpm
