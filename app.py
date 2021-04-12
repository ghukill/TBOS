"""
TBOS API
"""

import json
import time
import traceback
import uuid

from flask import Flask, request, jsonify
from flask_cors import CORS

from api.models import Bike, BikeSchema, LCD, PyboardClient, PybJobQueue, PybJobQueueSchema, Ride, RideSchema
from api.utils import parse_query_payload

from api.db import db


def create_app():

    app = Flask(__name__)

    # setup db
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///db/tbos.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)
    app.db = db

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

        # clear job queue
        PybJobQueue.stop_all_jobs()

        try:
            LCD.write("Welcome to TBOS", "status:ready")
        except Exception as e:
            print("LCD ERROR")
            print(str(e))
            print(traceback.format_exc())

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
    @app.route("/api/heartbeat", methods=["GET", "POST"])
    def hearbeat():

        t1 = time.time()

        # init heartbeat
        response = {}

        # get bike status
        t0 = time.time()
        response.update(Bike.current().get_status(to_lcd=False))
        print(f"bike status elapsed: {time.time()-t0}")

        # get ride status
        t0 = time.time()
        ride = Ride.current()
        if ride is None:
            ride = Ride.get_free_ride()
        response.update(ride.get_status())
        print(f"ride status elapsed: {time.time() - t0}")

        # if POST request, update Ride information
        if request.method == "POST":
            ta0 = time.time()
            payload = parse_query_payload(request)
            print(payload)
            ride.completed = payload["localRide"]["completed"]
            ride.save()
            print(f"ride update elapsed: {time.time() - ta0}")

        # lcd report
        # TODO: perform after flask response
        t0 = time.time()
        LCD.write(
            f"""c:{int(response["ride"]["completed"])}, r:{int(response["ride"]["remaining"])}""",
            f"""l:{response['rm']['level']}, rpm:{int(response['rpm']['rpm'])}""",
        )
        print(f"LCD write elapsed: {time.time() - t0}")

        # return
        print(f"heartbeat elapsed: {time.time()-t1}")
        return jsonify(response)

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

        # create new Ride
        ride = Ride(
            ride_uuid=str(uuid.uuid4()),
            name=payload.get("name", None),
            duration=duration,
        )

        # create
        ride.save()

        # set as current
        ride.set_as_current()

        # serialize and return
        return jsonify(ride.serialize())

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
        return jsonify(ride.serialize())

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
        return jsonify(ride.serialize())

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

    @app.route("/api/bike/rpm", methods=["GET"])
    def api_rpm_get():

        """
        Get bike RPM reading
        """

        response = Bike.current().get_rpm()
        return jsonify(response)

    @app.route("/api/jobs", methods=["GET"])
    def api_jobs_retrieve():

        """
        Return all jobs
        """

        return jsonify(PybJobQueueSchema(many=True).dump(PybJobQueue.query.all()))

    # return Flask app instance
    return app
