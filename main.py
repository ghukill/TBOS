"""
TBOS pyboard v1
"""

import pyb

from controller.embedded import move_to_level_position

# init vcp communicator
# TODO: consider communications file in controller directory
vcp = pyb.USB_VCP()

# main loop
while True:

    # listen delay
    pyb.delay(200) 
    if vcp.any() > 0:
        
        # data incoming, pause to finish then read
        pyb.delay(100)
        data = vcp.readline()

        # if data is an integer between 0-19, move motor position 
        ddata = data.decode()
        if int(ddata) in list(range(0,20)):
            result_tup = move_to_level_position(int(ddata))
            vcp.write(("position change: %s" % (str(result_tup))).encode())
        
        # responsd
        vcp.write(("unhandled command: %s" % (data.decode())).encode())
        pyb.delay(200) # wait for pi to gobble