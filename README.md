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

Migrations are run via flask-migrate

Help commands:
```bash
source venv/bin/activate
flask db --help
```

history
```bash
flask db history
4a1ce83f57dd -> b6ff6a01eca6 (head), add last segment
874e571003f9 -> 4a1ce83f57dd, add timestamp mark to heartbeat
1f1244f19928 -> 874e571003f9, sample program ride
acc54e65be2a -> 1f1244f19928, initial data
<base> -> acc54e65be2a, first migration
```

#### Setup systemctl service

Create systemctl service file @ `/lib/systemd/system/tbos.service`:
```
[Unit]
Description=TBOS API
After=multi-user.target

[Service]
Type=idle
Environment="PYTHONPATH=."
WorkingDirectory=/home/pi/dev/projects/TBOS
ExecStart=/home/pi/dev/projects/TBOS/venv/bin/flask run

[Install]
WantedBy=multi-user.target
```

Reload daemon and enable service
```bash
sudo systemctl daemon-reload
sudo systemctl enable tbos.service
sudo systemctl start tbos.service
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

#### Logging

```bash
journalctl -u tbos.service
```

#### Virtual Bike

By default, `recreate_db()` will create three bikes, where the default bike is a "virtual" bike that is not actually connected to an external controller.  This bike will allow the API to return results *as if* it were connected, with simulated delays.

### API Routes

See [Postman collection export](./api/TBOS.postman_collection.json)

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
