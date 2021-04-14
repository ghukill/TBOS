"""
TBOS: main embedded driver
"""

import json
import time

import pyb

# from embedded.lcd import init_lcd
from embedded.resistance_motor import goto_level, rm_status
from embedded.rpm_sensor import get_rpm


vcp = pyb.USB_VCP()
# vcp.setinterrupt(-1) # NOTE: might need if 3...


def serial_response(response):
    vcp.write(json.dumps(response).encode())


while True:

    # if anything in serial bus, parse
    if vcp.any() > 0:

        # debug
        t0 = time.time()

        # default
        error = None

        try:
            # toggle serial work LED
            pyb.LED(3).on()

            # wait for data to complete
            pyb.delay(50)

            # parse input data
            raw_input = vcp.readline()

            # parse request JSON
            request = json.loads(raw_input)

            # adjust level and/or get rm status
            pyb.LED(2).on()
            if request.get("level", None) is not None:
                rm = goto_level(
                    request["level"],
                    request.get("lower_bound", 100),
                    request.get("upper_bound", 3800),
                    request.get("pwm", 60),
                    request.get("sweep_delay", 0.006),
                    request.get("settle_threshold", 10),
                    debug=False,
                )
            else:
                rm = rm_status(
                    request.get("lower_bound", 100),
                    request.get("upper_bound", 3800),
                )
            pyb.LED(2).off()

            # get rpm
            if not request.get("skip_rpm", False):
                pyb.LED(4).on()
                rpm = get_rpm()
                pyb.LED(4).off()

            # build response
            response = {"request": request, "rm": rm, "rpm": rpm, "error": error}

        except Exception as e:
            # build response
            response = {"error": str(e), "raw_input": raw_input}

        # write response over serial
        response["elapsed"] = time.time() - t0
        serial_response(response)

        # toggle serial work LED
        pyb.LED(3).off()

    # main loop delay
    pyb.delay(50)
