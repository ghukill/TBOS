# TBOS

## Reference
  * Pyboard pins: http://micropython.org/resources/pybv11-pinout.jpg
  * Awesome-MicroPython (list of libs): https://awesome-micropython.com/

## Data Flow
```
GUI <--> Flask API <--> embedded Pyboard controller
```

## API

TBOS API is a Flask app providing HTTP endpoints.  Most all routes expect/return JSON.  The API is the primary mechanism for sending commands to the embedded Pyboard controller.

Persisted data is stored in a SQLlite database @ `./db/tbos.db`.

### Install
#### Create Virtual Environment
```bash
# create virtual environment
python3.7 -m venv venv

# source it
source venv/bin/activate

# pip installs
pip install -r requirements.txt
```

#### Create Database via Flask shell

Start flask shell:
```bash
source venv/bin/activate
flask shell
```

Create tables:
```python
from api.utils import recreate_db
recreate_db()
```

#### Run

Run on `localhost:5000`:
```bash
source venv/bin/activate
flask run
```

Bind to `0.0.0.0` so accessible on network:
```bash
source venv/bin/activate
flask run --host 0.0.0.0
```

#### Virtual Bike

By default, `recreate_db()` will create three bikes, where the default bike is a "virtual" bike that is not actually connected to an external controller.  This bike will allow the API to return results *as if* it were connected, with simulated delays.

### API Routes

See Postman collection: TODO FILE HERE

### TBOS API Flask shell

Start Flask shell:
```bash
source venv/bin/activate
flask shell
```

Usage
```python
# send level adjustment to embedded controller
from api.models import Bike
Bike.adjust_level(15)
```


## GUI

The GUI is a web application that provides a user interface to TBOS.  The GUI will send user inputs to the API, which in turns stores this information and passes along as necessary to the embedded controller.

GUI Github repository: _ADD LINK HERE_

## TODO

  * update RPM sensor logic to measure time between last two pings, instead of sampling 10s
  * 