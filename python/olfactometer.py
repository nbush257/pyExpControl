"""
Interface directly with the olfactometer over serial USB.

The olfactometer can run the same firmware as it would if interfacting via the nebPod main controller
Teensy board. Using this class sends the Serial message that is normally sent over UART from the main controller to the olfactometer,
thus we don't need multiple firmwares if we want to interact with the olfactometer directly without the other
functionality/hardware.

The class Olfactometer inherits from the Controller class defined in nebPod.py

No gui for this class currently exists. One can interface over command line:
`
    port = "COM11"
    olfactometer = Olfactometer(port)
    olfactometer.open_olfactometer(1)
    olfactometer.close_olfactometer(1)
`

Or use the olfactometer in a script:
`
    from olfactometer import Olfactometer
    port = "COM11"
    olfactometer = Olfactometer(port)
    olfactometer.open_olfactometer(1)
    olfactometer.close_olfactometer(1)
`
"""

import os
import sys
from pathlib import Path

from nebPod import Controller, event_timer, logger

curr_dir = Path(os.getcwd())
sys.path.append(str(curr_dir))
sys.path.append(str(curr_dir.parent.joinpath("ArCOM/Python3")))


class Olfactometer(Controller):
    """
    A class to interact with the olfactometer hardware.

    The Olfactometer class inherits from the Controller class defined in nebPod.py. It provides methods to open and close olfactometer valves.
    We have to redefine the open_olfactometer and close_olfactometer methods because the Serial message is different than the one sent to the main controller.

    Attributes:
        port (str): The port to which the olfactometer is connected.

    Methods:
        open_olfactometer(valve, verbose=True):
            Open an olfactometer valve.

        close_olfactometer(valve, verbose=True):
            Close an olfactometer valve.
    """

    def __init__(self, port):
        super().__init__(port)
        self.set_all_olfactometer_valves("00000000")

    @logger
    @event_timer
    def open_olfactometer(self, valve, verbose=True):
        """
        Open an olfactometer valve.

        Args:
            valve (int): The valve number to open.
            verbose (bool, optional): Verbosity flag. If True, prints the valve number. Defaults to True.

        Returns:
            tuple: A tuple containing:
                - label (str): 'open_olfactometer_valve'
                - params_out (dict): Dictionary with 'valve' key and the valve number as value.
        """
        self.serial_port.serialObject.write("o".encode("utf-8"))  # open
        self.serial_port.write(int(valve), "uint8")

        print(f"Opens olfactometer valve {valve}") if verbose else None
        self.block_until_read()
        return ("open_olfactometer_valve", "odor", {"valve": valve})

    @logger
    @event_timer
    def close_olfactometer(self, valve, verbose=True):
        """
        Close an olfactometer valve.

        Args:
            valve (int): The valve number to close.
            verbose (bool, optional): Verbosity flag. If True, prints the valve number. Defaults to True.

        Returns:
            tuple: A tuple containing:
                - label (str): 'close_olfactometer_valve'
                - params_out (dict): Dictionary with 'valve' key and the valve number as value.
        """
        self.serial_port.serialObject.write("c".encode("utf-8"))  # close
        self.serial_port.write(int(valve), "uint8")

        print(f"Closes olfactometer valve {valve}") if verbose else None
        self.block_until_read()
        return ("close_olfactometer_valve", "odor", {"valve": valve})

    @logger
    @event_timer
    def set_all_olfactometer_valves(self, binary_string, verbose=True):
        """
        Set all valves of the olfactometer with a single command.

        This method takes a binary string where '0' represents a closed valve and '1' represents an open valve.
        The string should be ordered such that the leftmost bit corresponds to Valve 1 and the rightmost bit corresponds to Valve 8.
        The string is reversed before sending due to bit ordering requirements.

        Args:
            binary_string (str): Binary string representing the state of each valve.
            verbose (bool, optional): Verbosity flag. If True, prints the binary string. Defaults to True.

        Returns:
            tuple: A tuple containing:
                - label (str): 'set_all_olfactometer_valves'
                - category (str): 'odor'
                - params_out (dict): Dictionary with 'binary_string' key and the binary string as value.
        """
        assert len(binary_string) == 8, "Binary string must be 8 characters long."
        binary_string_revr = binary_string[::-1]
        decimal_value = int(binary_string_revr, 2)
        self.serial_port.serialObject.write("b".encode("utf-8"))  # open
        self.serial_port.write(decimal_value, "uint8")

        print(f"Sets all valves to {binary_string}") if verbose else None
        self.block_until_read()
        return ("set_all_valves", "odor", {"valve": binary_string})
