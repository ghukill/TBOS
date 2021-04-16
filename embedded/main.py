"""
TBOS: main embedded driver
"""

import json
import time

import pyb

from embedded.lcd import init_lcd
from embedded.resistance_motor import goto_level, rm_status
from embedded.rpm_sensor import get_rpm


vcp = pyb.USB_VCP()


def serial_response(response):
    response_str = json.dumps(response) + "EOM"
    vcp.write(response_str.encode())


def time_elapsed(t0):
    return (time.ticks_ms() / 1000) - (t0 / 1000)


# init lcd
lcd = init_lcd()
lcd.clear()

# warmup: clear serial buffer
lcd.simple_write("TBOS warming...", None)
t0 = time.ticks_ms()
r = vcp.recv(19, timeout=10000)  # what are these 19 characters!?
pyb.delay(2000)
lcd.simple_write("TBOS ready!", "c %s ms %s" % (str(len(r)), time_elapsed(t0)))

# main loop
while True:

    # if anything in serial bus, parse
    if vcp.any() > 0:

        # debug
        t0 = time.ticks_ms()

        # init LCD outputs
        l1 = None
        l2 = None

        # init raw_response
        raw_response = None

        # init response
        response = {"error": None, "sender": "pyboard"}

        try:
            # toggle serial work LED
            pyb.LED(3).on()

            # wait for data to complete
            pyb.delay(50)

            # parse input data
            raw_input = vcp.readline()

            # parse request JSON
            try:
                request = json.loads(raw_input)
            except:
                lcd.simple_write("ERROR: JSON", "")
                pyb.delay(1000)
                try:
                    raw_input = raw_input.decode()
                except:
                    pass
                lcd.simple_write(">> %s" % raw_input[:12], raw_input[12:])
                pyb.delay(1000)
                lcd.clear()
                continue

            # if read message is sent by pyboard, ignore
            if request.get("sender", None) == "pyboard":
                lcd.simple_write("self serial:", "ignoring...")
                pyb.delay(1000)
                lcd.clear()
                continue

            elif request.get("lcd", None) is not None:
                l1 = request["lcd"]["l1"]
                l2 = request["lcd"]["l2"]

            else:

                # tag as heartbeat
                response["hb"] = True

                # adjust level and/or get rm status
                pyb.LED(2).on()
                if request.get("level", None) is not None:
                    rm = goto_level(
                        request.get("level", None),
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
        response.update({"elapsed": time_elapsed(t0)})

        # write response over serial
        serial_response(response)

        # write to LCD
        lcd.simple_write(l1, l2)

    # toggle LEDs and delay
    for x in [2, 3, 4]:
        pyb.LED(x).off()
    pyb.delay(10)
