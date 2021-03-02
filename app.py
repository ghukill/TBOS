"""
TBOS API
"""

import time

from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy

from api.models import Bike, Ride

from api.db import db


def create_app():

    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///db/tbos.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)
    app.db = db

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

    @app.route("/api/rm/adjust/<level>", methods=["GET"])
    def api_rm_adjust_level(level):
        """
        Adjust level
        """
        response = Bike.current().adjust_level(int(level))
        return jsonify(response)

    @app.route("/api/rpm", methods=["GET"])
    def api_rpm_get():
        """
        Get RPM reading
        """
        response = Bike.current().get_rpm()
        return jsonify(response)

    # return Flask app instance
    return app
