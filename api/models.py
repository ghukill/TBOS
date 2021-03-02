"""
TBOS API models
"""

import datetime
import json
import serial
import uuid

import flask

import pyboard
from rshell.main import is_micropython_usb_device

from .db import db
from .exceptions import PybReplCmdError, PybReplRespError

app = flask.current_app


class PyboardClient:

    """
    Client to interface with Pyboard via pyboard / rshell
    """

    def __init__(self):

        # automatically detect port
        self.pyboard_port = self.detect_pyboard_port()

        # setup pyb interface
        try:
            self.pyb = pyboard.Pyboard(self.pyboard_port, 115200)
        except:
            print("WARNING: cannot access pyboard")
            self.pyb = None

    def detect_pyboard_port(self):
        """
        Method to determine serial port pyboard is located on

        Inspired by rshell code:
        https://github.com/dhylands/rshell/blob/master/rshell/main.py#L350-L366
        """
        for port in serial.tools.list_ports.comports():
            if port.vid:
                if is_micropython_usb_device(port):
                    port = port.device
                    print(f"pyboard found @ {port}")
                    return port
        return None

    def repl_ping(self):

        """
        Send have repl print "pong"
        """

        return self.execute([("print('pong')", "string")], resp_idx=0)

    def execute(self, cmds, resp_idx=None, debug=False):

        """
        Issue passed command(s), aggregating responses and returning
        :param cmds: list of tuples, (cmd, response format)
            - e.g. [('repl_ping()', 'string'), ('give_me_json()', 'json')]
        :param resp_ids: int, optional, if present return only that response from the response list
        """

        # begin repl session
        self.pyb.enter_raw_repl()

        # loop through commands, execute, and handle response
        responses = []

        for cmd, response_format in cmds:
            try:
                response = self.pyb.exec(cmd)
                if debug:
                    print(response)

                # if response format is None, continue without touching response
                if response_format is None:
                    continue

                # decode and rstrip response
                response = response.decode()
                response = response.rstrip()

                # handle types
                if response_format == "json":
                    response = json.loads(response)
                if response_format == "int":
                    response = int(response)
                if response_format == "float":
                    response = float(response)

                # append to responses
                responses.append(response)
            except Exception as e:
                self.pyb.exit_raw_repl()
                raise PybReplCmdError(cmd)

        # close repl
        self.pyb.exit_raw_repl()

        # return responses
        if resp_idx is not None:
            try:
                return responses[resp_idx]
            except Exception as e:
                raise PybReplRespError(str(e))
        else:
            return responses


class Bike(db.Model):

    """
    Model to represent the bike / machine
    """

    bike_uuid = db.Column(db.String, primary_key=True, default=str(uuid.uuid4()))
    name = db.Column(db.Text, nullable=False)
    config = db.Column(
        db.Text,
        nullable=False,
        default={
            "resistance_motor": {"lower_bound": 245, "upper_bound": 610, "voltage": 9},
            "rpm_sensor": {},
        },
    )

    @classmethod
    def adjust_level(self, level):

        """
        Adjust resistance level
        """

        if not 0 <= level <= 20:
            raise Exception(f"level {level} is not between 0 to 20")

        # init client
        pc = PyboardClient()

        # execute
        response = pc.execute(
            [
                ("from embedded.resistance_motor import goto_level", None),
                (f"goto_level({level})", "json"),
            ],
            resp_idx=0,
        )

        # response
        return response

    @classmethod
    def get_rpm(self):

        """
        Get RPM sensor reading
        """

        # init client
        pc = PyboardClient()

        # execute
        response = pc.execute(
            [
                ("from embedded.rpm_sensor import *", None),
                (f"get_rpm()", "json"),
            ]
        )[0]

        # response
        return response

    def get_status(self):
        pass


class Ride(db.Model):

    """
    Model to represent a ride
    """

    ride_uuid = db.Column(db.String, primary_key=True, default=str(uuid.uuid4()))
    name = db.Column(db.Text, nullable=True)
    date_start = db.Column(db.DateTime, nullable=False, default=datetime.datetime.now())
    date_end = db.Column(db.DateTime, nullable=True)
    duration = db.Column(db.Float, nullable=False, default=30.0)


class PybJobQueue(db.Model):

    """
    Model for queued pyboard commands

    Columns
        - cmds: JSON array of commands, identical to what clients.PyboardClient.execute() expects
        - status: enum of strings
            - "queued": queued job, not yet run
            - "running": job is running
            - "success": job completed successfully
            - "failed": job failed
    """

    job_uuid = db.Column(db.String, primary_key=True, default=str(uuid.uuid4()))
    date_start = db.Column(db.DateTime, nullable=False, default=datetime.datetime.now())
    cmds = db.Column(db.Text, nullable=False)
    resps = db.Column(db.Text, nullable=True)
    resp_idx = db.Column(db.Integer, nullable=True)
    status = db.Column(db.String, default="queued", nullable=False)

    def execute(self, raise_exceptions=False):

        # mark as in_progress
        self.status = "running"
        app.db.session.commit()

        # init PyboardClient
        pc = PyboardClient()

        try:

            # execute
            response = pc.execute(json.loads(self.cmds), resp_idx=self.resp_idx)

            # mark as successfully
            self.status = "success"
            self.resps = json.dumps(response)  # QUESTION: is this right?  what if response is JSON?
            app.db.session.commit()

            # return response
            return response

        # TODO: better error handling
        except Exception as e:

            # mark as failed
            self.status = "failed"
            app.db.session.commit()

            # raise exception or return None
            if raise_exceptions:
                raise e
            else:
                return None
