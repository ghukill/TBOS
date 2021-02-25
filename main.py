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
        
        # data incoming, pause, read, decode
        pyb.delay(100)
        data = vcp.readline()
        ddata = data.decode()

        # if data is an integer between 0-19, move motor position 
        try:
            ddata_int = int(ddata)
            if ddata_int in list(range(0,20)):
                result_tup = move_to_level_position(ddata_int)
                vcp.write(("position change: %s" % (str(result_tup))).encode())
        except:
            pass

        # respond with unhandled
        vcp.write(("unhandled command: %s" % (data.decode())).encode())
        pyb.delay(200) # wait for pi to gobble