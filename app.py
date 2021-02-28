"""
TBOS GUI Flask app
"""

import time

from flask import Flask, request
from flask import render_template

# import serial
# ser = serial.Serial('/dev/ttyACM0', 9600, timeout=1)

from embedded.driver import direct_move


app = Flask(__name__)


@app.route("/", methods=["GET", "POST"])
def index():

    if request.method == "GET":
        return render_template("index.html")

    if request.method == "POST":

        level = request.values.get("level", None)

        # # move via serial
        # ser.flush()
        # ser.write(level.encode('utf-8'))
        # while True:
        #     msg = ser.readline()
        #     if msg != b'':
        #         break
        # msg = msg.decode('utf-8')

        # move via repl execution
        msg = direct_move(int(level))

        return render_template("index.html", msg=msg)
