"""
TBOS: main embedded driver
"""

import json
import time

import pyb

from embedded.debug import repl_ping
from embedded.lcd import HD44780
from embedded.resistance_motor import read_position_sensor, goto_level, rm_status
from embedded.rpm_sensor import get_rpm

# init LCD screen
lcd = HD44780()
lcd.PINS = ["Y1", "Y2", "Y3", "Y4", "Y5", "Y6"]


def status(lower_bound, upper_bound):

    """
    Return full sensor status
    """

    t0 = time.time()
    rm_reading = rm_status(lower_bound, upper_bound)
    rpm_reading = get_rpm(print_results=False)
    response = {"rm": rm_reading, "rpm": rpm_reading, "elapsed": time.time() - t0}

    # write to LCD
    try:
        lcd.init()
        l1 = "lev:%s, cur:%s" % (str(response["rm"]["level"]), str(response["rm"]["current"]))
        l2 = "rpm:%s" % (str(response["rpm"]["rpm"]))
        lcd.write(
            [l1, l2],
            clear=True,
        )
    except Exception as e:
        lcd.write(["ERROR", str(e)])

    # print and return
    print(json.dumps(response))
    return response
