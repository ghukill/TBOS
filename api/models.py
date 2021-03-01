"""
TBOS API models
"""

import datetime
import uuid

import flask

app = flask.current_app

from .clients import PyboardClient
from .db import db


class Bike(db.Model):

    """
    Class to represent the bike / machine
    """

    bike_uuid = db.Column(db.String, primary_key=True, default=str(uuid.uuid4()))
    name = db.Column(db.Text, nullable=False)
    config = db.Column(
        db.JSON,
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
        TODO: limit by config in Bike model
        """

        # init client
        pc = PyboardClient()

        # execute
        response = pc.execute(
            [
                ("from embedded.resistance_motor import goto_level", None),
                (f"goto_level({level})", "json"),
            ]
        )[0]

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
    Class to represent a ride
    """

    ride_uuid = db.Column(db.String, primary_key=True, default=str(uuid.uuid4()))
    name = db.Column(db.Text, nullable=True)
    date_start = db.Column(db.DateTime, nullable=False, default=datetime.datetime.now())
    date_end = db.Column(db.DateTime, nullable=True)
    duration = db.Column(db.Float, nullable=False, default=30.0)
