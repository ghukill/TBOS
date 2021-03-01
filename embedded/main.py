"""
TBOS: main embedded driver
"""

import pyb

from embedded.debug import repl_ping
from embedded.resistance_motor import read_position_sensor, goto_level
from embedded.rpm_sensor import get_rpm


# # main loop
# while True:
#
#     # debug RPM sensor
#     pyb.delay(5000)
#     print(get_rpm())
