"""
TBOS API models
"""

from collections import namedtuple
import datetime
import json
import random
import serial
import time
import traceback
import uuid

import flask
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema

import pyboard
from rshell.main import is_micropython_usb_device
from sqlalchemy import asc, desc

from .db import db
from .exceptions import PybReplCmdError, PybReplRespError

app = flask.current_app


def timestamp_now():
    return int(time.time())


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

        return self.execute([("from main import repl_ping", None), ("repl_ping()", "string")], resp_idx=0)

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

    default_config = {
        "virtual": False,
        "rm": {
            "lower_bound": 100,
            "upper_bound": 3800,
            "pwm_level": 75,
            "settled_threshold": 30,
        },
        "rpm": {},
    }

    bike_uuid = db.Column(db.String, primary_key=True, default=str(uuid.uuid4()))
    name = db.Column(db.Text, nullable=False)
    config = db.Column(
        db.Text,
        nullable=False,
        default=default_config,
    )
    is_current = db.Column(db.Boolean, default=0, nullable=False)

    def __repr__(self):
        return f"<Bike, {self.name}>"

    def set_as_current(self):

        """
        Method to set bike as current
        """

        # if already current, do nothing
        if self.is_current:
            return True

        # set all to False
        try:
            app.db.session.execute(
                """
                update bike set is_current=0
                """
            )

            # set self to current and commit
            self.is_current = True
            app.db.session.commit()
            return True
        except Exception as e:
            app.db.session.rollback()
            raise e

    @classmethod
    def current(cls):
        """
        Class Method to return the debug servo as a Bike instance
        """
        return cls.query.filter(cls.is_current == True).one_or_none()

    @property
    def _config(self):
        return json.loads(
            json.dumps(json.loads(self.config)), object_hook=lambda d: namedtuple("BikeConfig", d.keys())(*d.values())
        )

    @property
    def is_virtual(self):
        return self._config.virtual

    def get_status(self, raise_exceptions=False):

        """
        Get status report from embedded controller
        """

        # create and run job
        if self.is_virtual:
            level = 10
            current = int(((self._config.rm.upper_bound - self._config.rm.lower_bound) / 20) * level)
            rm = {"level": level, "current": current}
            response = {"rm": rm, "rpm": self.get_rpm()}
        else:
            response = PybJobQueue.create_and_run_job(
                [
                    (
                        f"status({self._config.rm.lower_bound}, {self._config.rm.upper_bound})",
                        "json",
                    )
                ],
                resp_idx=0,
                raise_exceptions=raise_exceptions,
            )

        # return
        return response

    def adjust_level(self, level, raise_exceptions=False):

        """
        Adjust resistance level
        """

        if not 0 <= level <= 20:
            raise Exception(f"level {level} is not between 0 to 20")

        # create and run job
        if self.is_virtual:
            time.sleep(2)
            target = int(((self._config.rm.upper_bound - self._config.rm.lower_bound) / 20) * level)
            response = {
                "loop_count": 10,
                "level": level,
                "current": target + random.randint(-15, 15),
                "target": target,
            }
        else:
            response = PybJobQueue.create_and_run_job(
                [
                    (
                        f"goto_level({level}, {self._config.rm.lower_bound}, {self._config.rm.upper_bound}, {self._config.rm.pwm_level}, {self._config.rm.settled_threshold})",
                        "json",
                    )
                ],
                resp_idx=0,
                raise_exceptions=raise_exceptions,
            )

        # return
        return response

    def get_rpm(self, raise_exceptions=False):

        """
        Get RPM sensor reading
        """

        # create and run job
        if self.is_virtual:
            time.sleep(random.randint(1, 3))
            response = {"rpm": 59.88304, "us_to_rpm_ratio": 5044.834, "us_diffs": [139592, 162508]}
        else:
            response = PybJobQueue.create_and_run_job(
                [(f"get_rpm()", "json")], resp_idx=0, raise_exceptions=raise_exceptions
            )

        # return response
        return response


class Ride(db.Model):

    """
    Model to represent a ride
    """

    ride_uuid = db.Column(db.String, primary_key=True, default=str(uuid.uuid4()))
    name = db.Column(db.Text, nullable=True)
    date_start = db.Column(db.DateTime, nullable=False, default=datetime.datetime.now)
    date_end = db.Column(db.DateTime, nullable=True, default=None)
    duration = db.Column(db.Float, nullable=False, default=30.0)
    completed = db.Column(db.Float, nullable=False, default=0.0)

    def save(self):
        try:
            app.db.session.add(self)
            app.db.session.commit()
        except Exception as e:
            app.db.session.rollback()
            raise e


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
    timestamp_added = db.Column(db.Integer, nullable=False, default=timestamp_now)
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
    def create_and_run_job(cls, cmds, resp_idx=None, timeout=10, raise_exceptions=False):

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
                response = job.execute(raise_exceptions=raise_exceptions)
                return response

            # else, continue to poll
            else:
                time.sleep(1)
                count += 1


###############################################
# SCHEMAS
###############################################
class BikeSchema(SQLAlchemyAutoSchema):
    # TODO: parse config JSON to dictionary
    class Meta:
        model = Bike
        include_relationships = True
        load_instance = True


class RideSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Ride
        include_relationships = True
        load_instance = True


class PybJobQueueSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Ride
        include_relationships = True
        load_instance = True
