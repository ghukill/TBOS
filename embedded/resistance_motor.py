"""
Resistance Motor
"""

import json
import time

import pyb

# define pins
pos = pyb.ADC(0)
enable = pyb.Pin("X2")
tim = pyb.Timer(2, freq=1000)
ch = tim.channel(2, pyb.Timer.PWM, pin=enable)
in1 = pyb.Pin("X3", pyb.Pin.OUT_PP)
in2 = pyb.Pin("X4", pyb.Pin.OUT_PP)

# turn off
ch.pulse_width_percent(0)
in1.low()
in2.low()


def read_position_sensor(num_reads=5, read_delay=0.05):

    """
    Sample sensor value multiple times rapidly, average, and return
    """

    reads = []
    for x in range(0, num_reads):
        reads.append(pos.read())
        time.sleep(read_delay / num_reads)
    current = sum(reads) / num_reads
    return current


def determine_step(lower_bound, upper_bound, step_num=20):

    """
    Based on upper and lower bounds, determine level sweep
    """

    return round(((upper_bound - lower_bound) - 1) / step_num)


def goto_level(level, lower_bound, upper_bound, pwm_level, settled_threshold, debug=False):

    """
    :param pwm_level: percentage of input 9v (9v @ 50% = 5.69v)
    """

    # bail if bounds not set
    if lower_bound is None or upper_bound is None:
        msg = "lower or upper bounds not set, bailing"
        print(msg)
        return msg

    # determine step
    step = determine_step(lower_bound, upper_bound)

    # determine target
    target = upper_bound - ((level - 1) * step)

    prev_diff = 0
    loop_count = 0
    while True:

        loop_count += 1

        # get sensor value
        current = read_position_sensor()

        diff = current - target
        if debug:
            print(
                "Target: %s, Current: %s, Prev Diff: %s, Diff: %s, Change: %s"
                % (target, current, prev_diff, diff, (prev_diff - diff))
            )
        prev_diff = diff

        # determine if settled
        if abs(diff) < settled_threshold:
            ch.pulse_width_percent(0)
            in1.low()
            in2.low()
            if debug:
                print("settled")
            break

        else:
            ch.pulse_width_percent(pwm_level)

            if current < target:
                in1.high()
                in2.low()
            else:
                in1.low()
                in2.high()

            time.sleep(0.01)  # NOTE: ideally this would be parameterized for bike as well
            in1.low()
            in2.low()

    # print/return response
    response = {
        "loop_count": loop_count,
        "level": level,
        "current": current,
        "target": target,
    }
    print(json.dumps(response))
    return response


def rm_status(lower_bound, upper_bound):

    """
    Function to return status
    """

    # get current reading
    current = read_position_sensor()

    # calculate level
    step = determine_step(lower_bound, upper_bound)
    level = round((upper_bound - current) / step) + 1

    return {"level": level, "current": current}
