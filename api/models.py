"""
TBOS API models
"""

from collections import namedtuple
import datetime
import json
import os
import random

import pandas as pd
import serial
import time
import traceback
import uuid

import boto3
import flask
import geopy.distance as geopy_distance
from gpx_converter import Converter
from marshmallow.decorators import pre_dump, pre_load
from marshmallow import fields
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema, auto_field

import pyboard
from rshell.main import is_micropython_usb_device
from sqlalchemy import asc, desc, ForeignKey
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import relationship
import sqlite3

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

        # DEBUG
        t0 = time.time()

        # automatically detect port
        self.pyboard_port = self.detect_pyboard_port()

        # set serial timeouts
        self.serial_timeout = 20

        # setup pyb interface
        try:
            self.pyb = pyboard.Pyboard(self.pyboard_port, 115200)
            self.pyb.serial.timeout = self.serial_timeout
        except:
            print("WARNING: cannot access pyboard")
            self.pyb = None

        print(f"time to init PyboardClient: {time.time()-t0}")

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

    def execute(self, cmds, resp_idx=None, debug=True):

        """
        Issue passed command(s), aggregating responses and returning
        :param cmds: list of commands (each a dict)
        :param resp_ids: int, optional, if present return only that response from the response list
        """

        # loop through commands, execute, and handle response
        responses = []

        for cmd in cmds:
            try:

                response = self.write_serial(cmd)

                if debug:
                    print(response)

                # append to responses
                responses.append(response)

            except Exception as e:
                raise Exception("ERROR WITH SERIAL JOB WRITE")  # TODO: error handling for bad serial write

        # return responses
        if resp_idx is not None:
            try:
                return responses[resp_idx]
            except Exception as e:
                raise PybReplRespError(str(e))
        else:
            return responses

    def soft_reboot(self):

        """
        Soft reboot
        """

        print("soft rebooting")
        self.pyb.enter_raw_repl()
        self.pyb.exit_raw_repl()
        return True

    def write_serial(self, msg_dict, followup=True):

        """
        Write serial data to pyboard, assuming all writes will be encoded JSON

        :param msg_dict: dictionary to write
        """

        # append sender
        msg_dict["sender"] = "client"

        # clear buffer
        self.pyb.serial.flushInput()

        # write msg_dict
        receipt = self.pyb.serial.write(json.dumps(msg_dict).encode())

        # followup and return
        if followup:
            response = self.read_serial()

        else:
            response = None
        return response

    def read_serial(self, nibble_timeout=3):

        """
        Receive JSON message
            - end of message signature "EOM"
        """

        # wait for nibble from the pyboard
        nibble_timeout_start = time.time()
        while True:
            if time.time() - nibble_timeout_start > nibble_timeout:
                raise Exception("timeout exceeded for nibble response")
            elif self.pyb.serial.in_waiting == 3:
                bom_mark = self.pyb.serial.read(3)
                if bom_mark.decode() != "BOM":
                    raise Exception("pyboard response BOM mark not correct")
                print("nibble received")
                break
            else:
                time.sleep(0.01)

        # poll for raw response
        # NOTE: could do this manually, but it's an interesting approach
        raw_response = self.pyb.read_until(1, "EOM".encode(), timeout=self.serial_timeout)

        # if response is empty, return None
        if raw_response == b"":
            return None

        # parse JSON from response
        try:
            response = raw_response.decode()
            response = response.rstrip("EOM")
            response = json.loads(response)

            # note handled error
            if response.get("error", None) is not None:
                # print(f"ERROR DETECTED: {response['error']}")
                raise Exception({"response_error": response["error"]})

        except Exception as e:
            print(raw_response)
            raise (e)

        # return
        return response


class Bike(db.Model):

    """
    Model to represent the bike / machine
    """

    default_config = {
        "virtual": True,
        "rm": {
            "lower_bound": 100,
            "upper_bound": 3800,
            "pwm_level": 75,
            "settled_threshold": 30,
            "sweep_delay": 0.006,
        },
        "rpm": {},
    }

    _level = None

    bike_uuid = db.Column(db.String, primary_key=True, default=str(uuid.uuid4()))
    name = db.Column(db.Text, nullable=False)
    config = db.Column(
        db.JSON,
        nullable=False,
        default=default_config,
    )
    is_current = db.Column(db.Boolean, default=0, nullable=False)
    last_status = db.Column(db.JSON, nullable=True)

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
            json.dumps(self.config), object_hook=lambda d: namedtuple("BikeConfig", d.keys())(*d.values())
        )

    @property
    def is_virtual(self):
        return self._config.virtual

    @property
    def level(self):

        """
        Property to return level, and retrieve from last status if none
        """

        if self._level is None:
            if self.last_status is not None:
                print("level is not set, using last stored")
                self._level = self.last_status["rm"]["level"]
            else:
                print("previous status not stored, retrieving")
                status = self.get_status()
                self._level = status["rm"]["level"]
        return self._level

    @property
    def random_virtual_rpm(self):

        return (random.randint(70, 80)) + random.random()

    def _generate_virtual_status(self, level=10):

        """
        Method to generate current status for virtual bike
        """
        current = int(((self._config.rm.upper_bound - self._config.rm.lower_bound) / 20) * level)
        rm = {"level": level, "current": current}
        virtual_status = {"rm": rm, "rpm": {"rpm": self.random_virtual_rpm}}
        self.last_status = virtual_status
        app.db.session.add(self)
        app.db.session.commit()
        return virtual_status

    def get_status(self, raise_exceptions=False):

        """
        Get status report from embedded controller about Bike
        """

        t0 = time.time()

        # create and run job
        if self.is_virtual:
            time.sleep(1)  # mimic read
            app.db.session.expire_all()  # expire to refresh
            if self.last_status is None:
                response = self._generate_virtual_status()
            else:
                response = self.last_status
            # random rpm
            response["rpm"]["rpm"] = self.random_virtual_rpm

        else:
            response = PybJobQueue.create_and_run_job(
                [
                    {
                        "level": None,
                        "lower_bound": self._config.rm.lower_bound,
                        "upper_bound": self._config.rm.upper_bound,
                    }
                ],
                resp_idx=0,
                raise_exceptions=raise_exceptions,
            )

        # update level
        self._level = response["rm"]["level"]

        # save to db
        self.last_status = response
        app.db.session.add(self)
        app.db.session.commit()

        # return
        print(f"get status elapsed: {time.time()-t0}")
        return response

    def adjust_level(self, level, raise_exceptions=False):

        """
        Adjust resistance level
        """

        if not 0 < level <= 20:
            raise Exception(f"level {level} is not between 0 to 20")

        # create and run job
        t0 = time.time()
        if self.is_virtual:
            time.sleep(1)
            response = self._generate_virtual_status(level)
        else:

            # get explicit target is present
            print(f"DEBUG: level from adjust_level: {level}")
            explicit_target = self.config["rm"].get("explicit_targets")[int(level) - 1]
            print(f"EXPLICIT TARGET: {explicit_target}")

            # send job
            response = PybJobQueue.create_and_run_job(
                [
                    {
                        "level": level,
                        "lower_bound": self._config.rm.lower_bound,
                        "upper_bound": self._config.rm.upper_bound,
                        "pwm": self._config.rm.pwm_level,
                        "sweep_delay": self._config.rm.sweep_delay,
                        "settle_threshold": self._config.rm.settled_threshold,
                        "explicit_target": explicit_target,
                    }
                ],
                resp_idx=0,
                raise_exceptions=raise_exceptions,
            )
        print(f"level adjust elapsed: {time.time()-t0}")

        # update level
        self._level = response["rm"]["level"]

        # save to db
        self.last_status = response
        app.db.session.add(self)
        app.db.session.commit()

        # return
        return response

    def adjust_level_down(self, raise_exceptions=False):

        """
        Decrease level by 1
        """

        # get current level
        level = self.level
        new_level = level - 1
        if new_level < 1:
            new_level = 1

        # adjust level
        response = self.adjust_level(new_level, raise_exceptions=raise_exceptions)

        # update level
        self._level = new_level

        # return
        return response

    def adjust_level_up(self, raise_exceptions=False):

        """
        Increase level by 1
        """

        # get current level
        level = self.level
        new_level = level + 1
        if new_level > 20:
            new_level = 20

        # adjust level
        response = self.adjust_level(new_level, raise_exceptions=raise_exceptions)

        # update level
        self._level = new_level

        # return
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
    cum_distance = db.Column(db.Float, nullable=False, default=0.0)
    is_current = db.Column(db.Boolean, default=0, nullable=False)
    program = db.Column(db.JSON, nullable=True)
    last_segment = db.Column(db.JSON, nullable=True)

    heartbeats = relationship("Heartbeat", back_populates="ride")
    # gpx_datas = relationship("GPXData", back_populates="ride")

    @property
    def total_distance(self):

        """
        If GPX ride, provide total distance
        """
        if self.gpx_df is not None:
            return self.gpx_df.iloc[-1].cum_distance
        else:
            return 0.0

    @property
    def gpx_df(self):

        """
        Return GPX data as parsed dataframe
        """

        # if not yet retrieved, retrieve
        if getattr(self, "_gpx_df", None) is None:
            print("loading GPX data as dataframe")
            df = pd.read_sql(
                f"""
                select * from gpx_data
                where ride_uuid='{str(self.ride_uuid)}'
                order by time;
                """,
                con=db.engine,
            )
            if len(df) == 0:
                self._gpx_df = None
            else:
                self._gpx_df = df

        return self._gpx_df

    def get_gpx_map_details(self):

        """
        Generate data for front-end maps from GPX dataset
        """

        if self.gpx_df is None:
            return None

        # get bounding box for all points
        bbox = [
            [self.gpx_df.latitude.max(), self.gpx_df.longitude.min()],
            [self.gpx_df.latitude.min(), self.gpx_df.longitude.max()],
        ]

        # get center point
        cp = ((bbox[0][0] + bbox[1][0]) / 2, (bbox[1][1] + bbox[0][1]) / 2)

        # initial marker
        marker = [self.gpx_df.iloc[0].latitude, self.gpx_df.iloc[0].longitude]

        # all points
        route_points = [[row.latitude, row.longitude] for row in self.gpx_df.itertuples()]

        return {"bbox": bbox, "cp": cp, "marker": marker, "route_points": route_points}

    @property
    def ride_type(self):

        ride_type = "random_duration"
        if self.gpx_df is not None:
            ride_type = "gpx"
        return ride_type

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
                update ride set is_current=0
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
        Class Method to return current Ride
        """
        return cls.query.filter(cls.is_current == True).one_or_none()

    def serialize(self, include_heartbeats=False):

        """
        Custom serialization for Ride
        """

        # init base as serialized data from db
        ser = RideSchema().dump(self)

        # add remaining node
        remaining = self.duration - self.completed
        if remaining < 0:
            remaining = 0
        ser["remaining"] = remaining

        # include heartbeats data
        if include_heartbeats:
            hb_data = [(hb.timestamp_added, hb.level, hb.rpm, hb.mark) for hb in self.heartbeats]
            ser["hb_data"] = hb_data

        # return
        return ser

    def save(self):
        try:
            app.db.session.add(self)
            app.db.session.commit()
        except Exception as e:
            app.db.session.rollback()
            raise e

    @classmethod
    def get_latest(cls):

        """
        Method to return latest ride and set as current
        """

        # get ride
        ride = cls.query.order_by(desc(cls.date_start)).first()

        # set as current
        ride.set_as_current()

        return ride

    @classmethod
    def get_current(cls):

        """
        Method to return latest ride and set as current
        """

        # get ride
        ride = cls.query.order_by(desc(cls.date_start)).first()

        # set as current
        ride.set_as_current()

        return ride

    def get_status(self, include_heartbeats=False):

        """
        Return Ride status
        """

        return {"ride": self.serialize(include_heartbeats=include_heartbeats)}

    @classmethod
    def get_free_ride(cls):

        """
        Return transient, "free" Ride instance
        """

        # mint UUID
        free_ride_uuid = str(uuid.uuid4())

        # create and save
        free_ride = cls(
            name=f"Free Ride {free_ride_uuid}",
            ride_uuid=free_ride_uuid,
            date_start=datetime.datetime.now(),
            duration=0.0,
            completed=0.0,
        )
        free_ride.save()

        # set as current
        free_ride.set_as_current()

        # return
        return free_ride

    @classmethod
    def generate_random_program(cls, duration, low=1, high=20, segment_length_s=60):
        """
        Class method to generate a random program
        """

        # init program
        program = []

        # loop and create
        for x in range(0, duration, segment_length_s):
            program.append([random.randint(low, high), [x, (x + segment_length_s)]])

        # return
        return program

    @classmethod
    def generate_program_from_gpx(cls, gpx_df, duration):

        """
        Generate ride from GPX data
            - break into 15 segments
        """

        print("generating program for GPX data")

        # calc altitude delta
        step_distance_mean = gpx_df.step_distance.mean()
        gpx_df["altitude_delta"] = 0.0
        for i, r in enumerate(gpx_df.itertuples()):

            # first step
            if i == 0:
                ad = 0.0

            # no movement
            elif r.step_distance < 3:
                ad = 0.0

            else:
                lr = gpx_df.iloc[i - 1]
                ad = round((r.altitude - lr.altitude) * 2.2, 2)
                # ad = round(((r.altitude - lr.altitude) * 2.2) * ((step_distance_mean - r.step_distance) / 10 + 1), 2)

            # set ad
            gpx_df.loc[i, "altitude_delta"] = ad

        # loop through duration in chunks of segment_seconds; these become segments
        segment_seconds = int(duration / 200)
        program = []
        for x in range(0, int(duration), segment_seconds):

            # get time span
            time_span = [x, x + segment_seconds]

            # get cumulative altitude change
            cum_altitude_delta = gpx_df[
                (gpx_df.mark >= time_span[0]) & (gpx_df.mark < time_span[1])
            ].altitude_delta.sum()

            # equivalent level
            level = round(cum_altitude_delta, 0) + 8
            if level > 20:
                level = 20
            if level < 1:
                level = 1

            # create program segment
            program.append([level, time_span])

        # set last
        program[-1][1][1] = int(duration)

        # return
        return program

    def handle_program_segment(self, response, bike):

        """
        Method to perform actions based on heartbeat of a ride, if a program exists

        :param response: response from bike for hearbeat
        :param bike: Bike instane
        """

        # extract mark
        mark = response.get("ride", {}).get("completed")

        # if program exists and mark is known
        if self.program is not None and mark is not None:

            print(f"checking ride program for mark: {mark}")

            # get program segment
            segment = self.get_program_segment(mark)

            # get CURRENT level
            cur_level = response["rm"]["level"]

            # if current level != segment level, adjust
            if cur_level != segment["level"]:
                if self.ride_type != "gpx":
                    print(f"adjusting level to match segment: {cur_level} --> {segment['level']}")

                    # if new segment, adjust level (allows in-level manual adjusts to be sticky)
                    if segment["is_new"]:
                        segment["adjust_level"] = bike.adjust_level(segment["level"])
                else:
                    print(f"skipping program level adjustment, GPX ride")

            # return segment
            return segment

        else:
            return None

    def get_program_segment(self, mark):

        """
        Extract segment from program
        """

        segment = {"num": None, "level": None, "window": None, "is_new": False}

        for seg_num, _segment in enumerate(self.program):
            seg_level, seg_window = _segment[0], _segment[1]
            if mark >= seg_window[0] and mark < seg_window[1]:
                print(f"segment match for mark: {mark} in {seg_window}")
                segment.update({"num": seg_num, "level": seg_level, "window": seg_window})

                # determine if new segment
                if self.last_segment is None or segment["num"] != self.last_segment["num"]:
                    segment["is_new"] = True

        # return segment
        return segment

    def parse_recorded_timeseries(self):

        """
        Return program and recorded information by second

        :return: [(program_level, recorded_level, rpm)], where index of list is second
        """

        t0 = time.time()

        # init output
        output = [[None, None, None, None] for x in range(0, int(self.duration))]

        # handle no program
        if self.program is None:
            pass
            # output.extend([[None, None, None, None] for _ in range(0, len(self.heartbeats))])

        # else, loop through segments and extend to per second
        else:
            output = []
            for segment in self.program:
                output.extend([[segment[0], None, None, None] for _ in range(segment[1][0], segment[1][1])])

        # interleave heartbeats
        for hb in self.heartbeats:
            try:
                output[hb.mark - 1][1] = hb.level
                output[hb.mark - 1][2] = hb.rpm
                output[hb.mark - 1][3] = hb.mph
            except:
                output.append([hb.mark, hb.level, hb.rpm, hb.mph])

        print(f"full level data elapsed: {time.time()-t0}")
        return output

    def get_bucketed_level_data(self, buckets=60):

        """
        Bucket level data to provide n buckets of data
        """

        pass

    @classmethod
    def create_random_duration_ride(cls, ride_uuid, payload, request):

        """
        Create random level, duration ride

        :return: Ride
        """

        # handle duration
        duration = int(payload.get("duration", 30)) * 60

        # handle random program
        random = {"on": True, "off": False}[payload.get("random", "on")]
        if random:
            program = cls.generate_random_program(
                duration,
                low=int(payload.get("level_low", 1)),
                high=int(payload.get("level_high", 20)),
                segment_length_s=int(payload.get("segment_length", 60)),
            )
        else:
            program = None

        # init and return ride
        return cls(
            ride_uuid=ride_uuid,
            name=payload.get("name", None),
            duration=duration,
            program=program,
        )

    @classmethod
    def create_gpx_ride(cls, ride_uuid, payload, request):

        """
        Create GPX path ride

        :return: Ride
        """

        # download file to tmp, then load as dataframe in memory
        print("saving GPX to disk and loading as dataframe")
        uf = request.files["gpx_file"]
        tmp_filepath = f"/tmp/{uf.filename}"
        with open(tmp_filepath, "wb") as f:
            f.write(uf.read())
        gpx_df = Converter(input_file=tmp_filepath).gpx_to_dataframe()
        os.remove(tmp_filepath)
        print(f"GPX loaded with {len(gpx_df)} data points")

        # convert time to timestamp
        # NOTE: this sets to seconds, not milliseconds
        gpx_df.time = gpx_df.time.apply(lambda x: int(x.timestamp()))

        # NOTE: slowish, consider reworking
        # calculate step and cumulative distances
        gpx_df["step_distance"] = 0.0
        for i, r in enumerate(gpx_df.itertuples()):
            if i == 0:
                d = 0.0
            else:
                lr = gpx_df.iloc[i - 1]
                d = geopy_distance.distance((lr.latitude, lr.longitude), (r.latitude, r.longitude)).feet
            gpx_df.loc[i, "step_distance"] = d
        gpx_df["cum_distance"] = gpx_df.step_distance.cumsum()

        # set mark for aligning
        min_time = gpx_df.time.min()
        gpx_df["mark"] = gpx_df.time - min_time
        gpx_df.mark = gpx_df.mark.astype(int)

        # add ride UUID
        gpx_df["ride_uuid"] = ride_uuid

        # mint uuids
        gpx_df["point_uuid"] = [str(uuid.uuid4()) for x in range(0, len(gpx_df))]

        # save rows to GPXData
        gpx_df.to_sql("gpx_data", con=db.engine, index=False, if_exists="append")

        # handle duration
        duration = int((gpx_df.time.max() - gpx_df.time.min()))

        # set program to NULL initially
        program = cls.generate_program_from_gpx(gpx_df, duration)

        # init and return ride
        return cls(
            ride_uuid=ride_uuid,
            name=payload.get("name", None),
            duration=duration,
            program=program,
        )


class Heartbeat(db.Model):

    """
    Model for heartbeat recordings
    """

    hb_uuid = db.Column(db.String, primary_key=True, default=str(uuid.uuid4()))
    timestamp_added = db.Column(db.Integer, nullable=False, default=timestamp_now)
    ride_uuid = db.Column(db.String, ForeignKey("ride.ride_uuid"), nullable=True)
    mark = db.Column(db.Integer, nullable=True)
    data = db.Column(db.JSON, nullable=True)
    level = db.Column(db.Integer, nullable=True)
    rpm = db.Column(db.Float, nullable=True)

    ride = relationship("Ride", back_populates="heartbeats")

    def save(self):
        try:

            # attempt extract of rm.level and rpm.rpm
            self.level = self.data.get("rm", {}).get("level", None)
            self.rpm = self.data.get("rpm", {}).get("rpm", None)

            app.db.session.add(self)
            app.db.session.commit()
        except Exception as e:
            app.db.session.rollback()
            raise e

    @property
    def mph(self):
        return self.data.get("speed", {}).get("mph")


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
            - "cancelled": job was cancelled
    """

    job_uuid = db.Column(db.String, primary_key=True, default=str(uuid.uuid4()))
    timestamp_added = db.Column(db.Integer, nullable=False, default=timestamp_now)
    cmds = db.Column(db.JSON, nullable=False)
    resps = db.Column(db.JSON, nullable=True)
    resp_idx = db.Column(db.Integer, nullable=True)
    status = db.Column(db.String, default="queued", nullable=False)
    priority = db.Column(db.Integer, nullable=True, default=1)

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

        # mark as running
        self.status = "running"
        app.db.session.commit()

        # init PyboardClient
        pc = PyboardClient()

        try:

            # execute
            response = pc.execute(self.cmds, resp_idx=self.resp_idx)

            # mark as successful
            self.status = "success"
            self.resps = response
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
    def create_and_run_job(cls, cmds, resp_idx=None, timeout=30, raise_exceptions=False):

        """
        Method to:
            1) create new job
            2) wait for any "running" jobs to complete
            3) execute job
            4) return results
        """

        # create new job
        job = PybJobQueue(job_uuid=str(uuid.uuid4()), cmds=cmds, resp_idx=resp_idx, status="queued")
        app.db.session.add(job)
        app.db.session.commit()

        # poll for other jobs to be complete
        timeout_start = time.time()
        while True:

            # if timeout, mark job as failed
            if (time.time() - timeout_start) > timeout:
                job.status = "failed"
                app.db.session.add(job)
                app.db.session.commit()
                raise Exception("timeout reached for creating and running new job")  # TODO: custom exception

            # check if no jobs running
            if cls.count_running_jobs() == 0:

                # execute job
                try:
                    response = job.execute(raise_exceptions=raise_exceptions)
                    return response
                except IntegrityError as integrity_error:
                    print(str(integrity_error))
                    app.db.session.rollback()
                    time.sleep(0.1)

            # else, continue to poll
            else:
                time.sleep(0.1)

    @classmethod
    def stop_all_jobs(cls):

        """
        Method to cancel all running jobs
        """

        all_jobs = cls.query.filter(cls.status.in_(["queued", "running"])).all()
        for job in all_jobs:
            job.status = "cancelled"
            app.db.session.add(job)
            app.db.session.commit()
        return len(all_jobs)

    @classmethod
    def get_next_queued(self):

        """
        Method to return the next queued job
        """

        # get next, ordered by priority and timestamp
        next = (
            PybJobQueue.query.filter(PybJobQueue.status == "queueud")
            .order_by(PybJobQueue.priority.desc())
            .order_by(PybJobQueue.timestamp_added.asc())
            .first()
        )

        return next


class LCD:
    def __init__(self):
        pass

    @classmethod
    def write(self, l1, l2, raise_exceptions=False):

        """
        Explicit two line message
        """

        response = PybJobQueue.create_and_run_job(
            [{"lcd": {"l1": l1, "l2": l2}}],
            raise_exceptions=raise_exceptions,
        )
        return response

    @classmethod
    def write_long(cls, msg, raise_exceptions=False):

        """
        Long or unknown length message
        """

        p = 0
        l = len(msg)

        while True:
            cls.write(msg[p : (p + 16)], msg[(p + 16) : (p + 32)])
            time.sleep(2)
            p += 32
            if p >= l:
                cls.write("EOM", f"len: {l}")
                break
        return l


class PollyTTS:
    def __init__(self):

        # setup aws session
        self.session = boto3.Session(profile_name="personal", region_name="us-east-1")

        # setup clients
        self.polly_client = self.session.client("polly")

        # voice
        self.voice_id = "Amy"

        # filesystem
        self.base_dir = "/tmp"
        if not os.path.exists(self.base_dir):
            os.mkdir(self.base_dir)

    @property
    def full_filepath(self):

        return f"{self.base_dir}/{self.filename}.mp3"

    def text_to_data(self, text):

        print("sending text to Polly")

        response = self.polly_client.synthesize_speech(
            VoiceId=self.voice_id, OutputFormat="mp3", Text=text, Engine="neural"
        )
        self.response = response

    def text_to_mp3(self, text):

        print("playing mpe")

        # mint filename
        self.filename = str(uuid.uuid3(uuid.NAMESPACE_OID, text))
        print(self.filename)

        if os.path.exists(self.full_filepath):
            print("loading pre-saved mp3")

        else:
            print("saving audio data as mp3")

            self.text_to_data(text)
            with open(self.full_filepath, "wb") as f:
                f.write(self.response["AudioStream"].read())

        return self.full_filepath


###############################################
# SCHEMAS
###############################################
class BikeSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Bike
        include_relationships = True
        load_instance = True


class RideSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Ride
        include_relationships = False
        load_instance = True


class PybJobQueueSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = PybJobQueue
        include_relationships = True
        load_instance = True


class HeartbeatSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Heartbeat
        include_relationships = True
        load_instance = True


class GPXData(db.Model):

    """
    Model for GPX data for a ride
    """

    __tablename__ = "gpx_data"

    # linkage
    point_uuid = db.Column(db.String, primary_key=True, default=str(uuid.uuid4()))
    ride_uuid = db.Column(db.String, ForeignKey("ride.ride_uuid"), nullable=False)

    # GPX provided
    time = db.Column(db.Integer, nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    altitude = db.Column(db.Float, nullable=False)

    # derived
    step_distance = db.Column(db.Float, nullable=True)
    cum_distance = db.Column(db.Float, nullable=True)
    mark = db.Column(db.Integer, nullable=True)

    # relationships
    # ride = relationship("Ride", back_populates="gpx_datas")
