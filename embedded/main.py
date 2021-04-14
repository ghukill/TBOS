"""
TBOS: main embedded driver
"""

import json
import sys
import time

import machine
import pyb

from embedded.lcd import init_lcd
from embedded.resistance_motor import goto_level, rm_status
from embedded.rpm_sensor import get_rpm


vcp = pyb.USB_VCP()
# vcp.setinterrupt(-1) # NOTE: might need if 3...


def serial_response(response):
    response_str = json.dumps(response) + "EOM"
    vcp.write(response_str.encode())


def handle_reboot(reboot_type):
    if reboot_type == "soft":
        sys.exit()
    elif reboot_type == "hard":
        machine.reset()


# init lcd
lcd = init_lcd()
lcd.clear()

while True:

    # if anything in serial bus, parse
    if vcp.any() > 0:

        # debug
        t0 = time.time()

        l1 = ""
        l2 = ""

        # init response
        response = {"error": None}

        try:
            # toggle serial work LED
            pyb.LED(3).on()

            # wait for data to complete
            pyb.delay(50)

            # parse input data
            raw_input = vcp.readline()

            # parse request JSON
            request = json.loads(raw_input)

            # handle soft reboot
            if request.get("reboot", None) is not None:
                handle_reboot(request["reboot"])

            elif request.get("lcd", None) is not None:
                l1 = request["lcd"]["l1"]
                l2 = request["lcd"]["l2"]

            else:
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
                pyb.LED(4).on()
                rpm = get_rpm()
                pyb.LED(4).off()

                # log heartbeat
                l1 = "hb l%s" % (str(int(rm["level"])))
                l2 = "rpm%s" % (str(int(rpm["rpm"])))

                # update response
                response.update({"request": request, "rm": rm, "rpm": rpm})

        except Exception as e:

            # write to LCD
            l1 = "ERROR: %s" % str(e)[:9]
            l2 = str(e)[9:]

            # update response
            response.update({"error": str(e), "raw_input": raw_input})

        # append elapsed
        response.update({"elapsed": time.time() - t0})

        # write response over serial
        serial_response(response)

        # write to LCD
        lcd.simple_write(l1, l2)

        # toggle LEDs
        for x in [2, 3, 4]:
            pyb.LED(x).off()

    # main loop delay
    pyb.delay(50)
