import serial

ser = serial.Serial('/dev/ttyACM0', 9600, timeout=1)

def pingpong(msg):
    ser.write(("%s\n" % msg).encode('utf-8'))
    while True:
        response = ser.readline()
        if response is not None:
            return response
