"""
TBOS API models
"""

import datetime
import json
import serial
import time
import uuid

import flask

import pyboard
from rshell.main import is_micropython_usb_device
from sqlalchemy import asc, desc

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

    def execute(self, cmds, resp_idx=None, skip_main_import=False, debug=False):

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

        # perform default imports on pyboard for repl session
        if not skip_main_import:
            self.pyb.exec("from main import *")

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

        # create and run job
        response = PybJobQueue.create_and_run_job([(f"goto_level({level})", "json")], resp_idx=0)
        return response

    @classmethod
    def get_rpm(self):

        """
        Get RPM sensor reading
        """

        # create and run job
        response = PybJobQueue.create_and_run_job([(f"get_rpm()", "json")], resp_idx=0)
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

    TODO
        - implement some form of "execute_now" that will:
            1) create a new job
            2) wait for all other "running" jobs to finish
            3) execute job
            4) return results
    """

    job_uuid = db.Column(db.String, primary_key=True, default=str(uuid.uuid4()))
    timestamp_added = db.Column(db.Integer, nullable=False, default=int(time.time()))
    cmds = db.Column(db.Text, nullable=False)
    resps = db.Column(db.Text, nullable=True)
    resp_idx = db.Column(db.Integer, nullable=True)
    status = db.Column(db.String, default="queued", nullable=False)

    @classmethod
    def count_running_jobs(cls):

        """
        Return count of running jobs
        """

        return cls.query.filter(cls.status == "running").count()

    def execute(self, raise_exceptions=False):

        """
        Execute a job
        """

        # bail if status is not queued
        if self.status != "queued":
            raise Exception(f"job status is {self.status}, skipping execution")

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
            self.resps = json.dumps(response)
            app.db.session.commit()

            # return response
            return response

        except Exception as e:

            # mark as failed
            self.status = "failed"
            app.db.session.commit()

            # raise exception or return None
            if raise_exceptions:
                raise e
            else:
                return None

    @classmethod
    def execute_queued(cls):

        """
        Method to retrieve and execute all queued jobs
        """

        # retrieve jobs ordered by timestamp added
        queued_jobs = cls.query.filter(cls.status == "queued").order_by(asc("timestamp_added")).all()

        # loop through and execute
        for job in queued_jobs:
            print(f"executing job: {job.job_uuid}")
            job.execute()

    @classmethod
    def create_and_run_job(cls, cmds, resp_idx=None, timeout=10):

        """
        Method to:
            1) create new job
            2) wait for any "running" jobs to complete
            3) execute job
            4) return results
        """

        # create new job
        job = PybJobQueue(
            job_uuid=str(uuid.uuid4()),
            cmds=json.dumps(cmds),
            resp_idx=resp_idx,
        )
        app.db.session.add(job)
        app.db.session.commit()

        # poll for other jobs to be complete
        count = 0
        while True:

            # if timeout, mark job as failed
            if count > timeout:
                job.status = "failed"
                app.db.session.add(job)
                app.db.session.commit()
                raise Exception("timeout reached for creating and running new job")  # TODO: custom exception

            # check if no jobs running
            if cls.count_running_jobs() == 0:

                # execute job
                response = job.execute()
                return response

            # else, continue to poll
            else:
                time.sleep(1)
                count += 1
