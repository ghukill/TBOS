"""
TBOS API
"""

import json
import os
import random
import time
import traceback
import uuid

from flask import Flask, request, jsonify, render_template, redirect, Response
from flask_cors import CORS
from flask_migrate import Migrate
import geopy.distance as geopy_distance
from gpx_converter import Converter
import pandas as pd

from api.models import (
    Bike,
    BikeSchema,
    LCD,
    PyboardClient,
    PybJobQueue,
    PybJobQueueSchema,
    Ride,
    RideSchema,
    Heartbeat,
    PollyTTS,
)
from api.utils import parse_query_payload, tbos_state_clear

from api.db import db


def create_app():

    app = Flask(__name__)

    # setup db
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///db/tbos.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)
    app.db = db

    # setup alembic migrations
    migrate = Migrate(app, db)

    # wrap in CORS
    CORS(app)

    # API Error Handling
    class InvalidUsage(Exception):
        """
        Class to assist with raising Exceptions as Flask HTTP responses,
        with user defined status codes
        """

        status_code = 400

        def __init__(self, message, status_code=None, payload=None):
            """
            Args:
                message: Exception message to be returned in JSON
                status_code: status code to set for HTTP response
                payload: optional payload to return in JSON response
            """
            Exception.__init__(self)
            self.message = message
            if status_code is not None:
                self.status_code = status_code
            self.payload = payload

        def to_dict(self):
            """
            Converts payload to dictionary
            Returns: (dict)
            """
            rv = dict(self.payload or ())
            rv["message"] = self.message
            return rv

    @app.errorhandler(InvalidUsage)
    def handle_invalid_usage(error):
        response = jsonify(error.to_dict())
        response.status_code = error.status_code
        return response

    app.InvalidUsage = InvalidUsage

    @app.errorhandler(Exception)
    def generic_exception(e):
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500

    # init
    with app.app_context():
        try:
            tbos_state_clear()
        except Exception as e:
            pass

    ######################################################################
    # Debug Routes
    ######################################################################
    @app.route("/", methods=["GET"])
    def debug_index():

        """
        TBOS
        """
        return f"TBOS"

    @app.route("/api/debug/ping", methods=["GET", "POST", "PATCH", "DELETE"])
    def debug_ping():

        """
        Ping/Pong
        """
        return f"{request.method} @ pong"

    @app.route("/api/debug/embedded/ping", methods=["GET"])
    def debug_embedded_ping():
        """
        Fire repl_ping from embedded controller
        """
        pyb = PyboardClient()
        resp = pyb.repl_ping()
        return resp

    @app.route("/api/debug/error", methods=["GET", "POST", "PATCH", "DELETE"])
    def debug_error():
        """
        Raise error
        """
        raise Exception("this is a debug error, do not be alarmed")

    ######################################################################
    # API Routes
    ######################################################################
    @app.route("/api/state_clear", methods=["GET", "POST"])
    def state_clear():

        """
        Route to clear state
        """

        tbos_state_clear()
        return jsonify({"msg": "TBOS state cleared", "success": True})

    @app.route("/api/heartbeat", methods=["GET", "POST"])
    def hearbeat():

        """
        Perform heartbeat
        """

        try:
            response = Heartbeat.perform_heartbeat(request)
            return jsonify(response)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/rides", methods=["GET"])
    def rides():

        """
        Retrieve all Rides
        """

        # serialize and return
        return jsonify([ride.serialize() for ride in Ride.query.all()])

    @app.route("/api/ride/new", methods=["POST"])
    def ride_new():

        """
        Create new Ride

        POST body:
        {
            "name": "super ride",
            "duration": 45.0
        }
        """

        # parse payload
        payload = parse_query_payload(request)

        # handle duration
        duration = payload.get("duration", None)
        if duration is not None:
            duration = int(duration)

        # handle random program
        if payload.get("program", {}).get("random", False):
            _p = payload["program"]
            program = Ride.generate_random_program(
                duration,
                low=_p["random_low"],
                high=_p["random_high"],
                segment_length_s=int(_p.get("random_segment_length", 60)),
            )
        else:
            program = None

        # create new Ride
        ride = Ride(ride_uuid=str(uuid.uuid4()), name=payload.get("name", None), duration=duration, program=program)

        # create
        ride.save()

        # set as current
        ride.set_as_current()

        # serialize and return
        return jsonify(ride.serialize(include_heartbeats=True))

    @app.route("/api/ride/<ride_uuid>", methods=["GET"])
    def ride_retrieve(ride_uuid):

        """
        Retrieve a single Ride and set as current
        """

        # retrieve a Ride
        ride = Ride.query.get(ride_uuid)
        if ride is None:
            raise app.InvalidUsage(f"ride {ride_uuid} was not found", status_code=404)

        # set as current
        if request.args.get("set_current", False):
            ride.set_as_current()

        # serialize and return
        return jsonify(ride.serialize(include_heartbeats=True))

    @app.route("/api/ride/current", methods=["GET"])
    def ride_retrieve_current():

        """
        Retrieve current Ride
        """

        # retrieve current Ride
        ride = Ride.get_latest()
        if ride is None:
            raise app.InvalidUsage(f"no rides found, cannot return current", status_code=404)

        # serialize and return
        return jsonify(ride.serialize(include_heartbeats=True))

    @app.route("/api/ride/current", methods=["PATCH"])
    def ride_current_update():

        """
        Update a single Ride via payload
        """

        # parse payload
        payload = parse_query_payload(request)

        # retrieve a Ride
        ride = Ride.current()
        if ride is None:
            raise app.InvalidUsage(f"no rides found, cannot update", status_code=404)

        # for key in payload, upload Ride
        for key, value in payload.items():
            setattr(ride, key, value)

        # save ride
        ride.save()

        # serialize and return
        return jsonify(ride.serialize())

    @app.route("/api/ride/<ride_uuid>", methods=["PATCH"])
    def ride_explicit_update(ride_uuid):

        """
        Update a single Ride via payload
        """

        # parse payload
        payload = parse_query_payload(request)

        # retrieve a Ride
        ride = Ride.query.get(ride_uuid)
        if ride is None:
            raise app.InvalidUsage(f"ride {ride_uuid} was not found", status_code=404)

        # for key in payload, upload Ride
        for key, value in payload.items():
            setattr(ride, key, value)

        # save ride
        ride.save()

        # serialize and return
        return jsonify(ride.serialize())

    @app.route("/api/bikes", methods=["GET"])
    def bikes():

        """
        Retrieve all bikes
        """

        # serialize and return
        return jsonify(BikeSchema(many=True).dump(Bike.query.all()))

    @app.route("/api/bike/set_current/<bike_uuid>", methods=["GET"])
    def bike_set_current(bike_uuid):

        """
        Set current bike
        """

        bike = Bike.query.get(bike_uuid)
        bike.set_as_current()
        return BikeSchema().dump(bike)

    @app.route("/api/bike/new", methods=["POST"])
    def bike_new():

        """
        Create new bike
        """

        pass

    @app.route("/api/bike/status", methods=["GET"])
    def api_status():

        """
        Get full status from embedded controller
        """

        response = Bike.current().get_status()
        return jsonify(response)

    @app.route("/api/bike/rm/adjust/<level>", methods=["GET"])
    def api_rm_adjust_level(level):

        """
        Adjust bike resistance motor level to explicit level
        """

        response = Bike.current().adjust_level(int(level))
        return jsonify(response)

    @app.route("/api/bike/rm/adjust/decrease", methods=["GET"])
    def api_rm_adjust_level_decrease():

        """
        Adjust bike resistance motor level - decrease by 1
        """

        print("decreasing level")
        response = Bike.current().adjust_level_down()
        return jsonify(response)

    @app.route("/api/bike/rm/adjust/increase", methods=["GET"])
    def api_rm_adjust_level_increase():

        """
        Adjust bike resistance motor level - increase by 1
        """

        print("increasing level")
        response = Bike.current().adjust_level_up()
        return jsonify(response)

    @app.route("/api/jobs", methods=["GET"])
    def api_jobs_retrieve():

        """
        Return all jobs
        TODO: this needs some limits, as this could grow quickly
        """

        return jsonify(PybJobQueueSchema(many=True).dump(PybJobQueue.query.all()))

    ######################################################################
    # GUI Routes
    ######################################################################
    @app.route("/gui", methods=["GET"])
    def gui_index():

        f = {}

        return render_template("index.html", title="TBOS", f=f, v=str(uuid.uuid4()))

    @app.route("/gui/rides", methods=["GET"])
    def gui_rides():

        # get current bike
        rides = Ride.query.order_by(Ride.date_start).all()

        # prepare variables
        f = {"rides": rides}

        return render_template("rides.html", title="TBOS", f=f, v=str(uuid.uuid4()))

    @app.route("/gui/rides", methods=["POST"])
    def gui_ride_create():

        print("creating new ride")

        # get input
        payload = request.form

        # mint ride uuid
        ride_uuid = str(uuid.uuid4())

        #########################################
        # RANDOM DURATION
        #########################################
        if payload["ride_type"] == "random_duration":

            ride = Ride.create_random_duration_ride(ride_uuid, payload, request)

        #########################################
        # GPX
        #########################################
        elif payload["ride_type"] == "gpx":

            ride = Ride.create_gpx_ride(ride_uuid, payload, request)

        # handle unknown ride_type
        else:
            raise Exception(f"ride_type {payload.get('ride_type')} not recognized")

        # create and set as current
        ride.save()
        ride.set_as_current()

        # redirect
        return redirect(f"/gui/ride/{ride.ride_uuid}")

    @app.route("/gui/ride/<ride_uuid>", methods=["GET"])
    def gui_ride(ride_uuid):

        ride = Ride.query.get(ride_uuid)
        ride.set_as_current()

        f = {"ride": ride}

        return render_template("ride.html", title="TBOS", f=f, v=str(uuid.uuid4()))

    @app.route("/gui/bike", methods=["GET"])
    def gui_bike():

        # get current bike
        bike = Bike.current()

        # prepare variables
        f = {"bike": bike}

        return render_template("bike.html", title="TBOS", f=f, v=str(uuid.uuid4()))

    @app.route("/gui/polly", methods=["GET"])
    def gui_polly():

        """
        Return MP3 binaay data
        """

        polly = PollyTTS()
        polly.text_to_data(request.args["text"])

        return Response(polly.response["AudioStream"].read(), mimetype="audio/mpeg")

    @app.route("/gui/testing/map", methods=["GET"])
    def testing_map():

        f = {}

        return render_template("testing/map.html", title="TBOS - map testing", f=f, v=str(uuid.uuid4()))

    # return Flask app instance
    return app
