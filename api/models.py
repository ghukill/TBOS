"""
TBOS API models
"""

import flask

app = flask.current_app

from .db import db


class Bike(db.Model):

    """
    Class to represent the bike / machine
        - configurations, presets, etc.
    """

    id = db.Column(db.String, primary_key=True)
    comment = db.Column(db.Text, nullable=True)

    def adjust_level(self):
        pass

    def get_status(self):
        pass


class Ride:

    """
    Class to represent a ride
    """
