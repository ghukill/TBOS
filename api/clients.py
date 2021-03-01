"""
TBOS API clients
"""

import json
import serial
import time

import pyboard
from rshell.main import is_micropython_usb_device, extra_info


class PybReplCmdError(Exception):
    pass


class PyboardClient:

    """
    Client to interface with Pyboard via pyboard / rshell
    """

    def __init__(self):

        # automatically detect port
        self.pyboard_port = self.detect_pyboard_port()

        # setup pyb interface
        try:
            self.pyb = pyboard.Pyboard(self.pyboard_port, 115200)
        except:
            print("WARNING: cannot access pyboard")
            self.pyb = None

    def detect_pyboard_port(self):
        """
        Method to determine serial port pyboard is located on

        Inspired by rshell code:
        https://github.com/dhylands/rshell/blob/master/rshell/main.py#L350-L366
        """
        for port in serial.tools.list_ports.comports():
            if port.vid:
                if is_micropython_usb_device(port):
                    port = port.device
                    print(f"pyboard found @ {port}")
                    return port
        return None

    def execute(self, cmds):

        """
        Issue passed command(s), aggregating responses and returning
        :param cmds: list of tuples, (cmd, response format)
            - e.g. [('repl_ping()', 'string'), ('give_me_json()', 'json')]
        """

        # begin repl session
        self.pyb.enter_raw_repl()

        # loop through commands, execute, and handle response
        responses = []

        for cmd, response_format in cmds:
            try:
                response = self.pyb.exec(cmd)
                print(response)

                # if response format is None, continue without touching response
                if response_format is None:
                    continue

                # decode and rstrip response
                response = response.decode()
                response = response.rstrip()

                # handle types
                if response_format == "json":
                    response = json.loads(response)
                if response_format == "int":
                    response = int(response)
                if response_format == "float":
                    response = float(response)

                # append to responses
                responses.append(response)
            except Exception as e:
                self.pyb.exit_raw_repl()
                raise PybReplCmdError(cmd)

        # close repl
        self.pyb.exit_raw_repl()

        # return responses
        return responses

    def repl_ping(self):

        """
        Send simple ping to repl_ping()
        """

        return self.execute(
            [("from embedded.debug import repl_ping", None), ("repl_ping()", "string")]
        )
