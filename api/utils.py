"""
TBOS API utils
"""

import traceback

import flask
from flask import jsonify

from api.models import Bike, LCD, PybJobQueue, PyboardClient

app = flask.current_app


def parse_query_payload(request):

    """
    Helper function to parse query payload
    """

    try:
        query_payload = request.json
    except:
        raise app.InvalidUsage(
            f"this {request.method} request must contain valid JSON as body of request", status_code=400
        )

    return query_payload


def recreate_db():

    """
    Function to (Re)Create the SQLlite database
        - drop tables if exist
        - create tables
        - initial inserts
    """

    # jit imports
    from .models import Bike

    # drop tables
    print("dropping tables")
    for table in ["bike", "ride", "pyb_job_queue"]:
        try:
            app.db.session.execute(f"drop table {table};")
            app.db.session.commit()
        except:
            print(f"could not drop table: {table}")
            app.db.session.rollback()

    # create tables
    print("creating tables")
    app.db.create_all()

    # insert Bikes
    print("inserting Bikes")
    debug_servo = Bike(
        bike_uuid="8933f238-5ebc-43a7-acc8-2d7272a5e81d",
        name="Debug Virtual",
        config={
            "virtual": True,
            "rm": {
                "lower_bound": 100,
                "upper_bound": 3800,
                "pwm_level": 75,
                "settled_threshold": 30,
                "sweep_delay": 0.006,
            },
            "rpm": {},
        },
        is_current=True,
    )
    app.db.session.add(debug_servo)
    debug_servo = Bike(
        bike_uuid="6e063089-438e-4a9b-a369-9db7bcf9a502",
        name="Debug Servo",
        config={
            "virtual": False,
            "rm": {
                "lower_bound": 100,
                "upper_bound": 3800,
                "pwm_level": 75,
                "settled_threshold": 30,
                "sweep_delay": 0.006,
            },
            "rpm": {},
        },
        is_current=False,
    )
    app.db.session.add(debug_servo)
    lf_c1 = Bike(
        bike_uuid="998ac153-f8be-436a-a1ca-4ec14874b181",
        name="LifeCycle C1",
        config={
            "virtual": False,
            "rm": {
                "lower_bound": 988,
                "upper_bound": 3773,
                "pwm_level": 100,
                "settled_threshold": 10,
                "sweep_delay": 0.04,
            },
            "rpm": {},
        },
        is_current=False,
    )
    app.db.session.add(lf_c1)
    app.db.session.commit()


def tbos_state_clear():

    """"""

    print("TBOS init")

    # clear job queue
    print("stopping all jobs...")
    PybJobQueue.stop_all_jobs()

    # clear last bike status
    print("clearing previous bike status...")
    app.db.session.execute(
        """
        update bike set last_status = null
        """
    )

    # clearing current rides
    print("clearing current ride...")
    app.db.session.execute(
        """
        update ride set is_current = 0
        """
    )

    # commit
    app.db.session.commit()

    # splash screen
    try:
        LCD.write("TBOS API", "ready!")
    except Exception as e:
        print("LCD ERROR")
        print(str(e))
        print(traceback.format_exc())

    print("TBOS init complete")
