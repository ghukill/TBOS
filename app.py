"""
TBOS API
"""

import json
import time
import traceback
import uuid

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_migrate import Migrate

from api.models import Bike, BikeSchema, LCD, PyboardClient, PybJobQueue, PybJobQueueSchema, Ride, RideSchema, Heartbeat
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
        tbos_state_clear()

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

        try:
            t1 = time.time()

            # init heartbeat
            response = {}

            # get bike status
            tb0 = time.time()
            response.update(Bike.current().get_status(raise_exceptions=True))
            print(f"bike status elapsed: {time.time()-tb0}")

            # get ride status
            tr0 = time.time()
            ride = Ride.current()
            if ride is None:
                ride = Ride.get_free_ride()
            response.update(ride.get_status())
            print(f"ride status elapsed: {time.time() - tr0}")

            # if POST request, update Ride information
            if request.method == "POST":
                ta0 = time.time()
                payload = parse_query_payload(request)
                print(payload)
                ride.completed = payload["localRide"]["completed"]
                ride.save()
                print(f"ride update elapsed: {time.time() - ta0}")

            # record heartbeat
            thb0 = time.time()
            hb = Heartbeat(hb_uuid=str(uuid.uuid4()), ride_uuid=ride.ride_uuid, data=response)
            hb.save()
            print(f"heartbeat recorded elapsed: {time.time() - thb0}")

            # check ride program, adjust level if needed
            # TODO: move all this to Ride method...
            mark = response.get("ride", {}).get("completed")
            if mark is not None:
                if ride.program is not None:
                    print(f"checking ride program for mark: {mark}")

                    # get current level
                    level = response["rm"]["level"]

                    # loop through program segments and see if currently within a segment
                    for segment in ride.program:
                        seg_level, seg_window = segment[0], segment[1]
                        if mark >= seg_window[0] and mark < seg_window[1]:
                            print(f"window match: {seg_window}")

                            # check if level different
                            # TODO: allow an override in a segment to "stick"
                            if level != seg_level:
                                print(f"adjusting level to match segment: {level} --> {seg_level}")

                                # get bike and adjust level
                                bike = Bike.current()
                                adjust_response = bike.adjust_level(seg_level)

            # return
            print(f"heartbeat elapsed: {time.time()-t1}")
            return jsonify(response)

        except Exception as e:
            print(str(e))
            print(traceback.format_exc())
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

    # return Flask app instance
    return app
