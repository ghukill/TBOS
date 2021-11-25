"""
TBOS API utils
"""

import traceback

import flask

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


def tbos_state_clear():

    """"""

    from api.models import LCD, PybJobQueue, Bike

    print("TBOS init")

    # clear job queue
    print("stopping all jobs...")
    try:
        PybJobQueue.stop_all_jobs()
    except Exception as e:
        print({"error": str(e), "traceback": traceback.format_exc()})

    # clear last bike status
    print("clearing previous bike status...")
    try:
        app.db.session.execute(
            """
            update bike set last_status = null
            """
        )
    except Exception as e:
        print({"error": str(e), "traceback": traceback.format_exc()})

    # print current bike
    current_bike = Bike.current()
    print(f"Current bike: {current_bike}")

    # clearing current rides
    print("clearing current ride...")
    try:
        app.db.session.execute(
            """
            update ride set is_current = 0
            """
        )
        app.db.session.execute(
            """
            update ride set last_segment = NULL
            """
        )
    except Exception as e:
        print({"error": str(e), "traceback": traceback.format_exc()})

    # commit
    app.db.session.commit()

    # splash screen
    try:
        LCD.write("TBOS API", "ready!")
    except Exception as e:
        print({"error": str(e), "traceback": traceback.format_exc()})

    print("TBOS init complete")
