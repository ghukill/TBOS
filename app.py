"""
TBOS API
"""

import time

from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy

from api.models import Bike, Ride

from api.db import db


def create_app():

    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///db/tbos.db"
    db.init_app(app)

    ######################################################################
    # Test Routes
    ######################################################################
    @app.route("/", methods=["GET"])
    def debug_index():

        """
        TBOS
        """
        return f"TBOS"

    @app.route("/debug/ping", methods=["GET", "POST", "PATCH", "DELETE"])
    def debug_ping():

        """
        Ping/Pong
        """
        return f"{request.method} @ pong"

    ######################################################################
    # Ride Routes
    ######################################################################
    @app.route("/ride/new", methods=["POST"])
    def ride_new():

        """
        Create new Ride
        """
        pass

    @app.route("/ride/<ride_uuid>", methods=["GET"])
    def ride_retrieve(ride_uuid):

        """
        Retrieve a Ride
        """
        pass

    ######################################################################
    # API Routes
    ######################################################################
    @app.route("/api/pyboard/ping", methods=["GET"])
    def api_pyboard_ping():

        """
        Ping pyboard, expect 'pong'
        """
        pass

    @app.route("/api/status", methods=["GET"])
    def api_status():

        """
        Retrieve current bike status
        """
        pass

    # return Flask app instance
    return app
