"""
TBOS: main embedded driver
"""

import json
import time

import pyb

# from embedded.debug import repl_ping
#
# from embedded.lcd import init_lcd
from embedded.resistance_motor import read_position_sensor, goto_level, rm_status
from embedded.rpm_sensor import get_rpm


vcp = pyb.USB_VCP()
# vcp.setinterrupt(-1) # NOTE: might need if 3...

while True:
    pyb.delay(50)  # listen delay

    if vcp.any() > 0:
        pyb.LED(3).on()
        pyb.delay(50)  # know data coming, wait for complete
        data = vcp.readline()

        # parse JSON
        try:
            request = json.loads(data)
        except:
            request = None

        # adjust level and/or get rm status
        pyb.LED(2).on()
        if request is not None and request["l"] is not None:
            rm = goto_level(request["l"], 100, 3800, 75, 0.004, 10, debug=False, print_response=False)
        else:
            rm = rm_status(100, 3880)
        pyb.LED(2).off()

        # get rpm
        pyb.LED(4).on()
        rpm = get_rpm(print_results=False)
        pyb.LED(4).off()

        response = {"request": request, "rm": rm, "rpm": rpm}
        vcp.write(json.dumps(response).encode())

        # pyb.delay(200)  # wait for pi to gobble
        pyb.delay(50)  # little bit of grace
        pyb.LED(3).off()
