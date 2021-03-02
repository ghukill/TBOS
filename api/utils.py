"""
TBOS API utils
"""

import json

import flask

app = flask.current_app


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
    app.db.session.execute("drop table bike;")
    app.db.session.execute("drop table ride;")
    app.db.session.execute("drop table pyb_job_queue;")
    app.db.session.commit()

    # create tables
    print("creating tables")
    app.db.create_all()

    # insert Bikes
    print("inserting Bikes")
    debug_servo = Bike(
        bike_uuid="6e063089-438e-4a9b-a369-9db7bcf9a502",
        name="Debug Servo",
        config=json.dumps(
            {
                "rm": {
                    "lower_bound": 100,
                    "upper_bound": 3800,
                    "pwm_level": 75,
                    "settled_threshold": 30,
                },
                "rpm": {},
            }
        ),
    )
    app.db.session.add(debug_servo)
    lf_c1 = Bike(
        bike_uuid="998ac153-f8be-436a-a1ca-4ec14874b181",
        name="LifeCycle C1",
        config=json.dumps(
            {
                "rm": {
                    "lower_bound": 245,
                    "upper_bound": 610,
                    "pwm_level": 75,
                    "settled_threshold": 30,
                },
                "rpm": {},
            }
        ),
    )
    app.db.session.add(lf_c1)
    app.db.session.commit()
