# TBOS

## Reference
  * Pyboard pins: http://micropython.org/resources/pybv11-pinout.jpg
  * Awesome-MicroPython (list of libs): https://awesome-micropython.com/

## Data Flow
```
GUI --> Flask API --> embedded pyboard
```

## API

TBOS API is a flask app providing HTTP endpoints.  Most all routes expect/return JSON.  The API also provides the primary mechanism for sending commands to the embedded pyboard controller.

### Install Virtual Environment
```python
# create virtual environment
python3.7 -m venv venv

# source it
source venv/bin/activate

# pip installs
pip install -r requirements.txt
```

### API Routes

### TBOS API shell
Start it:
```bash
# source virtual environment
source venv/bin/activate
# fire it up
flask shell
```

Usage
```python
# TODO...
```


## GUI

The GUI is a web application that provides a user interface to TBOS.  The GUI will send user inputs to the API, which in turns stores this information and passes along as necessary to the embedded controller.