
"""
Pin mappings are generally handled by teensy firmware, so this should be general.

When controller is instantiated, a log is started. It is a list of dicts that will get parsed into a pandas dataframe and saved as a .tsv:
e.g.:
| label           | category | start_time | end_time | param1 | param2 |
|-----------------|----------|------------|----------|--------|--------|
| start_recording | event    | 0          | 5        | None   | None   |
| present_gas     | gas      | 5          | 305      | O2     | None   |
| laser_train     | opto     | 305        | 307      | 20Hz   | 2s     |
| laser_train     | opto     | 337        | 339      | 20Hz   | 2s     |
| laser_train     | opto     | 367        | 369      | 20Hz   | 2s     |
| laser_train     | opto     | 397        | 399      | 20Hz   | 2s     |
| present_gas     | gas      | 579        | 879      | hypercapnia | None |
| stop_recording  | event    | 879        | 880      | None   | None   |

Methods for the controller can have decoraters to automatically get start (and optionally stop) times and append to the log.

e.g.:
    @interval_timer: appends start and stop times to the output of the function
    @event_timer: appends only the start time to the output of the function
    @logger: appends the output of the function to the log. Optionally (and by default) saves the log to a .tsv file on each call.

Example:
    @logger
    @interval_timer
    def function(self, param1, param2):
        # do something

        # parameters to save to the log
        params = dict(param1=param1, param2=param2)
        return (label, category, params)
"""
# TODO: extend and test functionality with thorlabs LED drivers (long term)
from ArCOM import ArCOMObject
import time
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pathlib import Path
from tqdm import tqdm
import datetime
import functools
import os
import sys
from pathlib import Path

curr_dir = Path(os.getcwd())
sys.path.append(str(curr_dir))
sys.path.append(str(curr_dir.parent.joinpath("ArCOM/Python3")))


def interval_timer(func):
    """
    Decorator that appends the start and stop time to the output of a function.
    Input function must output (label,category,params) where:
    label: descriptor of the function call
    category: descriptor of the function category (e.g., opto, event, gas)
    params: dictionary of parameters that the function was called with

    Thus the output is a dictionary with the following keys:
    label: descriptor of the function call
    category: descriptor of the function category (e.g., opto, event, gas)
    start_time: time the function was called
    end_time: time the function returned
    params: dictionary of parameters that the function was called with

    Args:
        func (function): The function to be decorated.

    Returns:
        function: The wrapped function with start and stop time appended to its output.
    """

    def wrapper(*args, **kwargs):
        start_time = time.time()
        label, category, params = func(*args, **kwargs)
        end_time = time.time()

        output = dict(
            label=label,
            category=category,
            start_time=start_time,
            end_time=end_time,
            **params,
        )
        return output

    return wrapper


def event_timer(func):
    """
    Decorator that appends the start time to the output of a function.

    Differs from interval timer in that only the start time is appended

    Input function must output (label,category,params) where:
    label: descriptor of the function call
    category: descriptor of the function category (e.g., opto, event, gas)
    params: dictionary of parameters that the function was called with

    Thus the output is a dictionary with the following keys:
    label: descriptor of the function call
    category: descriptor of the function category (e.g., opto, event, gas)
    start_time: time the function was called
    params: dictionary of parameters that the function was called with

    Args:
        func (function): The function to be decorated.

    Returns:
        function: The wrapped function with start time appended to its output.

    """

    def wrapper(*args, **kwargs):
        start_time = time.time()
        label, category, params = func(*args, **kwargs)
        output = dict(
            label=label,
            category=category,
            start_time=start_time,
            end_time=np.nan,
            **params,
        )
        return output

    return wrapper


def logger(func):
    """
    Decorator that appends output of a function call to the controller's "log" object.

    Args:
        func (function): The function to be decorated.

    Returns:
        function: The wrapped function with logging functionality.
    """

    def wrapper(self, *args, log_enabled=True, **kwargs):
        result = func(self, *args, **kwargs)
        if log_enabled:
            self.log.append(result)
            self.save_log(verbose=False)
        return result

    return wrapper


class Controller:
    """
    Controller class to manage the communication and control of the NPX rig.

    Represents a Teensy (or other microcontroller) that is used to control the NPX rig.

    Attributes:
        serial_port (ArCOMObject): The serial port object for communication.
        IS_CONNECTED (bool): Connection status.
        gas_map (dict): Mapping of teensy pin to gas.
        ADC_RANGE (int): ADC range.
        V_REF (float): Reference voltage.
        MAX_MILLIWATTAGE (float): Maximum milliwattage for the light meter.
        settle_time_sec (int): Default settle time in seconds.
        log (list): Log list to store function call outputs.
        rec_start_time (float): Recording start time.
        rec_stop_time (float): Recording stop time.
        gate_dest (Path): Destination path for gate data.
        gate_dest_default (str): Default destination path for gate data.
        log_filename (str): Log filename.
        init_time (float): Initialization time.
        laser_command_amp (float): Laser command amplitude.
        odor_map (dict): Mapping of odors.
    """

    def __init__(self, port, gas_map=None, cobalt_mode="S", null_voltage=0.4):
        """
        Initialize the Controller object.

        Args:
            port (str): The serial port for communication (e.g. COM11).
            gas_map (dict, optional): Mapping of teensy pin to gas. Defaults to None.
            cobalt_mode (str, optional): Mode for cobalt control. Defaults to "S".
            null_voltage (float, optional): Null voltage for cobalt control. Defaults to 0.4.
        """
        try:
            self.serial_port = ArCOMObject(
                port, 115200
            )  # Replace 'COM11' with the actual port of your Arduino
            self.IS_CONNECTED = True
            print("Connected!")
        except:
            self.IS_CONNECTED = False
            print(
                f"No Serial port found on {port}. GUI will show up but not do anything"
            )
        # Set the gas map if supplied. This maps the teensy pin to the gas
        self.gas_map = gas_map or {
            0: "O2",
            1: "room air",
            2: "hypercapnia",
            3: "hypoxia",
            4: "N2",
        }
        self.ADC_RANGE = 8191  # 13bit adc range (TODO: read from teeensy)
        self.V_REF = 3.3  # Teensy 3.2 vref
        self.MAX_MILLIWATTAGE = (
            310.0  # Thorlabs light meter max range to scale the photometer calibration
        )
        self.settle_time_sec = 15 * 60  # Default settle time
        self.log = []  # Initialize the log list
        self.rec_start_time = None
        self.rec_stop_time = None
        self.gate_dest = None
        self.gate_dest_default = "D:/sglx_data"
        self.log_filename = None
        self.init_time = time.time()
        if cobalt_mode == "B":
            null_voltage = 0
        self.init_cobalt(
            null_voltage=null_voltage
        )  # Initialize the laser controller object
        self.laser_command_amp = None
        self.odor_map = None

    @logger
    @event_timer
    def open_valve(self, valve_number, log_style=None):
        """
        Open a valve by its pin number on the teensy. Closes all other valves

        Args:
            valve_number (int): The pin number of the valve to open.
            log_style (str, optional): Style of logging. Defaults to None.

        Returns:
            dict: Output dictionary with function call details.
        """
        self.serial_port.serialObject.write("v".encode("utf-8"))
        self.serial_port.write(valve_number, "uint8")
        self.block_until_read()
        # Write to log as either the gas presented or the valve number opened.
        if log_style == "gas":
            label = f"{self.gas_map[valve_number]}"
        else:
            label = f"open_valve_{int(valve_number)}"
        return (label, "gas", {})

    @logger
    @event_timer
    def present_gas(self, gas, presentation_time=None, verbose=False, progress="bar"):
        """
        Blocking wrapper to open_valve that takes a gas name as input,
        and then sleeps the function for the presentation time.

        Args:
            gas (str): Gas name, must be a key in gasmap.
            presentation_time (float, optional): Presentation time in seconds. Defaults to None.
            verbose (bool, optional): Verbosity flag. Defaults to False.
            progress (str, optional): Progress display style. Defaults to "bar".

        Returns:
            dict: Output dictionary with function call details.
        """
        assert (
            gas in self.gas_map.values()
        ), f"requested gas is not available. Must be :{self.gas_map.values()}"
        # invert the dictionary to use gas to map to the valve
        inv_map = {v: k for k, v in self.gas_map.items()}

        print(f"Presenting {gas}") if verbose else None
        self.open_valve(inv_map[gas], log_enabled=False)
        if presentation_time is not None:
            self.wait(presentation_time, msg=f"Presenting {gas}", progress=progress)
        return (f"present_{gas}", "gas", {})

    @logger
    @event_timer
    def end_hb(self, verbose=False):
        """
        End the hering breuer stimulation by reopening the hering breuer valve.

        Assumes hering breuer valve is mapped in the teensy arduino code
        """

        print("End hering breuer") if verbose else None

        # Send the command to the teensy
        self.serial_port.serialObject.write("h".encode("utf-8"))
        self.serial_port.serialObject.write("e".encode("utf-8"))
        self.block_until_read()

        return ("end_heringbreuer", "event", {})

    @logger
    @event_timer
    def start_hb(self, verbose=False):
        """
        Start the hering breuer stimulation by closing the hering breuer valve.

        Assumes hering breuer valve is mapped in the teensy arduino code
        """
        print("start hering breuer") if verbose else None

        # Send the command to the teensy
        self.serial_port.serialObject.write("h".encode("utf-8"))
        self.serial_port.serialObject.write("b".encode("utf-8"))
        self.block_until_read()
        return ("start_heringbreuer", "event", {})

    @logger
    @interval_timer
    def timed_hb(self, duration, verbose=False):
        """
        Start and end a hering breuer stimulation by wrapping to the hering breuer sub-processes

        Assumes hering breuer valve is mapped in the teensy arduino code
        """
        print(f"Run hering breuer for {duration}s") if verbose else None

        self.start_hb(log_enabled=False)
        time.sleep(duration)
        self.end_hb(log_enabled=False)
        return ("hering_breuer", "event", {"duration": duration})
    
    @logger
    @interval_timer
    def phasic_stim_HB(
        self,
        phase,
        mode,
        n,
        duration_sec,
        intertrain_interval_sec=30.0,
        freq=None,
        pulse_duration_sec=None,
        verbose=False,
    ):
        """
        Run Hering Breuer (HB) stimulations that are triggered from the diaphragm activity.

        ONLY INSPIRATORY HOLDS ARE IMPLEMENTED

        Args:
            phase (str): Phase of the diaphragm activity. Must be 'e' (Expiratory) or 'i' (Inspiratory).
            mode (str): Stimulation mode. Must be 'h' (hold), 't' (train), or 'p' (pulse).
            n (int): Number of repetitions.
            duration_sec (float): Duration of the stimulation window in seconds.
            intertrain_interval_sec (float, optional): Time between stimulation windows in seconds. Defaults to 30.0.
            freq (float, optional): Frequency of pulse train if using train mode. Defaults to None.
            pulse_duration_sec (float, optional): Pulse duration if using "train" or "pulse" mode. Defaults to None.
            verbose (bool, optional): Verbosity flag. Defaults to False.

        Returns:
            dict: Output dictionary with function call details.
        """
        assert mode in ["h", "t", "p"], f"Stimulation mode {mode} not supported"
        assert phase in ["e", "i"], f"Stimulation trigger {phase} not supported"
        assert mode == "h", "Only hold mode is implemented for HB stimulations"
        assert (
            phase == "i"
        ), "Only inspiratory holds are implemented for HB stimulations"

        phase_map = {"e": "exp", "i": "insp"}
        mode_map = {"h": "hold", "t": "train", "p": "pulse"}

        # Handle the different modes
        if mode == "h":
            freq = None
            pulse_duration_sec = None
        if mode == "t":
            assert freq is not None, " frequency is needed for phasic  trains"
            assert (
                pulse_duration_sec is not None
            ), "pulse duration is needed for phasic  trains"
            pulse_dur_ms = sec2ms(pulse_duration_sec)
        if mode == "p":
            assert (
                pulse_duration_sec is not None
            ), "pulse duration is needed for phasic single pulses"
            pulse_dur_ms = sec2ms(pulse_duration_sec)
            freq = None
        if verbose:
            print(
                f"Running HB phasic stims:{phase_map[phase]},{mode_map[mode]},{freq=},{pulse_duration_sec=}"
            )

        if n == 1:
            intertrain_interval_sec = 0.0

        intertrain_interval_ms = sec2ms(intertrain_interval_sec)
        duration_ms = sec2ms(duration_sec)

        self.empty_read_buffer()
        self.serial_port.serialObject.write("a".encode("utf-8"))
        self.serial_port.serialObject.write("h".encode("utf-8"))
        self.serial_port.serialObject.write(phase.encode("utf-8"))
        self.serial_port.serialObject.write(mode.encode("utf-8"))
        self.serial_port.write(n, "uint8")
        self.serial_port.write(duration_ms, "uint16")
        self.serial_port.write(intertrain_interval_ms, "uint16")
        if mode == "t":
            self.serial_port.write(pulse_dur_ms, "uint8")
            self.serial_port.write(int(freq), "uint8")

        if mode == "p":
            self.serial_port.write(pulse_dur_ms, "uint8")

        self.block_until_read()

        label = "hering_breuer_phasic"
        params_out = dict(
            phase=phase_map[phase],
            mode=mode_map[mode],
            duration=duration_sec,
            frequency=freq,
            pulse_duration=pulse_duration_sec,
        )

        return (label, "event", params_out)

    def init_cobalt(
        self, mode="S", power_meter_pin=16, null_voltage=0.5, verbose=False
    ):
        """
        Initialize or modify the cobalt object in the Arduino.

        This method is particularly useful if you want to switch between sigmoidal and other modes.

        Args:
            mode (str, optional): Mode to set for the cobalt object. Defaults to 'S'. Can be 'S' (sigmoidal) or 'B' (binary).
            power_meter_pin (int, optional): Pin number for the power meter. Defaults to 16.
            null_voltage (float, optional): Null voltage value. Defaults to 0.5.
            verbose (bool, optional): Verbosity flag. If True, prints the initialization details. Defaults to False.

        Returns:
            None
        """
        null_voltage_uint8 = int(255 * null_voltage)
        self.serial_port.serialObject.write("c".encode("utf-8"))
        self.serial_port.serialObject.write("m".encode("utf-8"))
        self.serial_port.serialObject.write(mode.encode("utf-8"))
        self.serial_port.write(power_meter_pin, "uint8")
        self.serial_port.write(null_voltage_uint8, "uint8")
        self.block_until_read()
        print(
            f"initialized cobalt with mode {mode} and power meter pin {power_meter_pin}"
        ) if verbose else None

    @logger
    @event_timer
    def run_pulse(self, pulse_duration_sec, amp, verbose=False):
        """
        Run a single opto pulse via the Cobalt teensy controller.

        Args:
            pulse_duration_sec (float): Duration of the pulse in seconds.
            amp (float): Amplitude of the pulse (0-1).
            verbose (bool, optional): Verbosity flag. Defaults to False.

        Returns:
            dict: Output dictionary with function call details.
        """
        #  Convert to ms for arduino
        duration = sec2ms(pulse_duration_sec)
        print(f"Running opto pulse at {amp:.2f}V for {duration}ms") if verbose else None
        amp_int = self._amp2int(amp)

        # Send the command to the teensy
        self.serial_port.serialObject.write("p".encode("utf-8"))
        self.serial_port.write(duration, "uint16")
        self.serial_port.write(amp_int, "uint8")
        self.block_until_read()

        label = "opto_pulse"
        params_out = dict(amplitude=amp, duration=pulse_duration_sec)

        return (label, "opto", params_out)

    @logger
    @interval_timer
    def run_train(self, duration_sec, freq, amp, pulse_duration_sec, verbose=False):
        """
        Run a single train of opto pulses.

        Args:
            duration_sec (float): Full train duration in seconds.
            freq (float): Stimulation frequency in Hz.
            amp (float): Amplitude of the stimulation (0-1).
            pulse_duration_sec (float): Pulse duration in seconds.
            verbose (bool, optional): Verbosity flag. Defaults to False.

        Returns:
            dict: Output dictionary with function call details.
        """
        # Convert to ms for arduino
        duration = sec2ms(duration_sec)
        pulse_duration = sec2ms(pulse_duration_sec)

        print(
            f"Running opto train:\n\tAmplitude:{amp:.2f}V\n\tFrequency:{freq:.1f}Hz\n\tPulse duration:{pulse_duration}ms\n\tTrain duration:{duration_sec:.3f}s"
        ) if verbose else None

        self.empty_read_buffer()
        amp_int = self._amp2int(amp)

        # Send the command to the teensy
        self.serial_port.serialObject.write("t".encode("utf-8"))
        self.serial_port.write(duration, "uint16")
        self.serial_port.write(freq, "uint8")
        self.serial_port.write(amp_int, "uint8")
        self.serial_port.write(pulse_duration, "uint8")
        self.block_until_read()

        label = "opto_train"
        params_out = dict(
            amplitude=amp,
            duration=duration_sec,
            frequency=freq,
            pulse_duration=pulse_duration_sec,
        )
        return (label, "opto", params_out)

    @logger
    @interval_timer
    def run_tagging(
        self, n=75, pulse_duration_sec=0.050, amp=1.0, ipi_sec=3, verbose=True
    ):
        """
        Run a preset train that is specific for opto-tagging.

        Passes the parameters to the run_pulse function which sends the command to the teensy.

        Args:
            n (int, optional): Number of tagging stimulations. Defaults to 75.
            pulse_duration_sec (float, optional): Duration of stimulation in seconds. Defaults to 0.050.
            amp (float, optional): Amplitude of stimulation (0-1). Defaults to 1.0.
            ipi_sec (float, optional): Interpulse interval in seconds. Defaults to 3.
            verbose (bool, optional): Verbosity flag. Defaults to True.

        Returns:
            dict: Output dictionary with function call details.
        """
        pulse_duration_ms = sec2ms(pulse_duration_sec)

        if verbose:
            print("running opto tagging")
        self.empty_read_buffer()
        for ii in range(n):
            if verbose:
                print(f"\ttag {pulse_duration_ms}ms stim: {ii+1} of {n}. amp: {amp} ")
            self.run_pulse(pulse_duration_sec, amp, log_enabled=False)
            time.sleep(ipi_sec)

        label = "opto_tagging"
        params_out = dict(
            n_tags=int(n),
            amplitude=amp,
            pulse_duration=pulse_duration_sec,
            interpulse_interval=ipi_sec,
        )
        return (label, "opto", params_out)

    @logger
    @interval_timer
    def phasic_stim(
        self,
        phase,
        mode,
        n,
        amp,
        duration_sec,
        intertrain_interval_sec=30.0,
        freq=None,
        pulse_duration_sec=None,
        verbose=False,
    ):
        """
        Run stimulations that are triggered off of the diaphragm activity.

        Args:
            phase (str): Phase of the diaphragm activity. Must be 'e' (Expiratory) or 'i' (Inspiratory).
            mode (str): Stimulation mode. Must be 'h' (hold), 't' (train), or 'p' (pulse).
            n (int): Number of repetitions.
            amp (float): Amplitude of stimulation (0-1).
            duration_sec (float): Duration of the stimulation window in seconds.
            intertrain_interval_sec (float, optional): Time between stimulation windows in seconds. Defaults to 30.0.
            freq (float, optional): Frequency of pulse train if using train mode. Defaults to None.
            pulse_duration_sec (float, optional): Pulse duration if using "train" or "pulse" mode. Defaults to None.
            verbose (bool, optional): Verbosity flag. Defaults to False.

        Returns:
            dict: Output dictionary with function call details.

        """
        assert mode in ["h", "t", "p"], f"Stimulation mode {mode} not supported"
        assert phase in ["e", "i"], f"Stimulation trigger {phase} not supported"

        phase_map = {"e": "exp", "i": "insp"}
        mode_map = {"h": "hold", "t": "train", "p": "pulse"}

        # Handle the different modes
        if mode == "h":
            freq = None
            pulse_duration_sec = None
        if mode == "t":
            assert freq is not None, " frequency is needed for phasic  trains"
            assert (
                pulse_duration_sec is not None
            ), "pulse duration is needed for phasic  trains"
            pulse_dur_ms = sec2ms(pulse_duration_sec)
        if mode == "p":
            assert (
                pulse_duration_sec is not None
            ), "pulse duration is needed for phasic single pulses"
            pulse_dur_ms = sec2ms(pulse_duration_sec)
            freq = None
        if verbose:
            print(
                f"Running opto phasic stims:{phase_map[phase]},{mode_map[mode]},{freq=},{pulse_duration_sec=}"
            )

        if n == 1:
            intertrain_interval_sec = 0.0

        intertrain_interval_ms = sec2ms(intertrain_interval_sec)
        duration_ms = sec2ms(duration_sec)

        # Send the command to the teensy
        self.empty_read_buffer()
        amp_int = self._amp2int(amp)
        self.serial_port.serialObject.write("a".encode("utf-8"))
        self.serial_port.serialObject.write("p".encode("utf-8"))
        self.serial_port.serialObject.write(phase.encode("utf-8"))
        self.serial_port.serialObject.write(mode.encode("utf-8"))
        self.serial_port.write(n, "uint8")
        self.serial_port.write(duration_ms, "uint16")
        self.serial_port.write(intertrain_interval_ms, "uint16")
        self.serial_port.write(amp_int, "uint8")
        if mode == "t":
            self.serial_port.write(pulse_dur_ms, "uint8")
            self.serial_port.write(int(freq), "uint8")

        if mode == "p":
            self.serial_port.write(pulse_dur_ms, "uint8")

        self.block_until_read()

        label = f"opto_phasic"
        params_out = dict(
            phase=phase_map[phase],
            mode=mode_map[mode],
            amplitude=amp,
            duration=duration_sec,
            frequency=freq,
            pulse_duration=pulse_duration_sec,
        )

        return (label, "opto", params_out)

    def turn_on_laser(self, amp, verbose=False):
        """
        Turn on the laser with the specified amplitude.

        Args:
            amp (float): Amplitude of the laser, a float between 0-1 (v).
            verbose (bool, optional): Verbosity flag. If True, prints the amplitude. Defaults to False.
        """
        print(f"Turning on laser at amp: {amp}") if verbose else None
        amp_int = self._amp2int(amp)
        self.serial_port.serialObject.write("o".encode("utf-8"))
        self.serial_port.serialObject.write("o".encode("utf-8"))
        self.serial_port.write(amp_int, "uint8")
        self.block_until_read()

    def turn_off_laser(self, amp, verbose=False):
        """
        Turn off the laser from the specified amplitude.

        Args:
            amp (float): Amplitude of the laser, a float between 0-1 (v).
            verbose (bool, optional): Verbosity flag. If True, prints the amplitude. Defaults to False.
        """
        print(f"Turning off laser from amp: {amp}") if verbose else None
        amp_int = self._amp2int(amp)
        self.serial_port.serialObject.write("o".encode("utf-8"))
        self.serial_port.serialObject.write("x".encode("utf-8"))
        self.serial_port.write(amp_int, "uint8")
        self.block_until_read()

    def set_max_milliwattage(self, val):
        """
        Set the maximum milliwattage for calibrating the laser.

        This value is read from the Thorlabs light meter and is used to convert the voltage output from Thorlabs to milliwatts.

        Args:
            val (float): The maximum milliwattage value to set.
        """
        self.MAX_MILLIWATTAGE = val

    def poll_laser_power(self, amp, output="mw", verbose=False):
        """
        Turn on the laser and read a voltage-in to measure the laser power.

        Voltage-in read pin is managed by teensy firmware

        Args:
            amp (float): Amplitude of the laser, a float between 0-1 (v).
            output (str, optional): Units of output requested. Can be 'mw' for milliwatts or 'v' for voltage. Defaults to 'mw'.
            verbose (bool, optional): Verbosity flag. Defaults to False.

        Returns:
            float: The laser power in the requested units (milliwatts or voltage).
            int: The raw read from the Arduino if the output unit is not recognized.

        Raises:
            ValueError: If the amplitude is not between 0 and 1.
        """

        # Convert the amplitude to an integer
        amp_int = self._amp2int(amp)
        print(f"Testing amplitude: {amp}") if verbose else None

        # Send the command to the teensy
        self.serial_port.serialObject.write("o".encode("utf-8"))
        self.serial_port.serialObject.write("p".encode("utf-8"))
        self.serial_port.write(amp_int, "uint8")
        while self.serial_port.bytesAvailable() < 2:
            time.sleep(0.001)

        # Convert the serial uint16 read to a voltage or power
        power_int = self.serial_port.read(1, "uint16")  # Power as a 10bit integer
        power_v = power_int / self.ADC_RANGE * self.V_REF  # Powerr as a voltage
        power_mw = (power_v / 2.0) * self.MAX_MILLIWATTAGE  # power in milliwatts
        self.block_until_read()

        if output == "v":
            return power_v
        elif output == "mw":
            return power_mw
        else:
            print("returning read digital bit val")
            return power_int

    def auto_calibrate(
        self, amp_range=None, amp_res=0.01, plot=False, output="mw", verbose=False
    ):
        """
        Automatically calibrate the laser by proceeding through a sequence of command powers and reading the photometer output.

        Args:
            amp_range (list, optional): Upper and lower limits of the voltage command to test. Defaults to [0, 0.81].
            amp_res (float, optional): Resolution of voltages to sample (i.e., step sizes). Defaults to 0.01.
            plot (bool, optional): If true, plot the relationship between the voltage command and the output. Defaults to False.
            output (str, optional): Units of output requested. Can be 'mw' for milliwatts or 'v' for voltage. Defaults to 'mw'.
            verbose (bool, optional): Verbosity flag. Defaults to False.

        Returns:
            tuple: A tuple containing:
                - amps_to_test (numpy.ndarray): Array of command voltages tested.
                - powers (numpy.ndarray): Array of measured powers corresponding to the command voltages.
        """
        amp_range = amp_range or [0, 0.81]
        amps_to_test = np.arange(amp_range[0], amp_range[1], amp_res)
        # Add a zero to get background voltage
        amps_to_test = np.concatenate([[0], amps_to_test])

        # Initialize output
        powers = np.zeros_like(amps_to_test) * np.nan
        self.turn_off_laser(0)

        for ii, amp in enumerate(amps_to_test):
            power_mw = self.poll_laser_power(amp, verbose=verbose, output=output)
            powers[ii] = power_mw

        # Subtract off the first reading
        powers -= powers[1]

        # Plot the results
        if plot:
            f = plt.figure()
            plt.plot(amps_to_test[1:], powers[1:], "ko-")
            if output == "mw":
                plt.ylabel("Power (mw)")
                key_powers = [2.5, 5, 10]
                key_amp_idx = np.searchsorted(powers, key_powers)
                key_amps = amps_to_test[key_amp_idx - 1]
                print(key_amps)
                for aa, pp in zip(key_amps, key_powers):
                    plt.axvline(aa, color="tab:blue", ls="--")
                    plt.axhline(pp, color="tab:green", ls="--")
                    plt.text(0.25, pp, f"{aa:0.2f}v={pp:0.2f}mW")
                plt.ylim(-2, 20)

            else:
                plt.ylabel("Analog voltage read")
            plt.axhline(powers[1], color="r", ls="--")

            plt.xlabel("Command voltage (V)")
            plt.tight_layout()
            plt.show()

        return (amps_to_test, powers)

    @logger
    @interval_timer
    def play_tone(self, freq, duration_sec, verbose=False):
        """
        Play an arbitrary audio tone.

        Args:
            freq (float): Frequency of the tone in Hz.
            duration_sec (float): Duration of the tone in seconds.
            verbose (bool, optional): Verbosity flag. If True, prints the frequency and duration. Defaults to False.

        Returns:
            tuple: A tuple containing:
                - label (str): 'tone'
                - category (str): 'event'
                - params_out (dict): Dictionary with 'frequency' and 'duration' of the tone.
        """
        self.empty_read_buffer()
        duration_ms = sec2ms(duration_sec)
        print(
            f"Playing audio tone: frequency{freq}, duration:{duration_sec:.3f} (s)"
        ) if verbose else None
        self.serial_port.serialObject.write("aa".encode("utf-8"))
        self.serial_port.write(int(freq), "uint16")
        self.serial_port.write(int(duration_ms), "uint16")
        self.block_until_read()

        label = "tone"
        params_out = dict(frequency=freq, duration=duration_sec)
        return (label, "event", params_out)

    @logger
    @interval_timer
    def play_alert(self, verbose=False):
        """
        Play a predefined audio tone to alert the user.

        Args:
            verbose (bool, optional): Verbosity flag. If True, prints the frequency and duration. Defaults to False.

        Returns:
            tuple: A tuple containing:
                - label (str): 'audio_alert'
                - category (str): 'event'
                - params_out (dict): Dictionary with 'frequency' and 'duration' of the alert tone.
        """
        freq = 1000
        duration = 0.500
        self.play_tone(freq, duration, verbose=verbose, log_enabled=False)

        label = "audio_alert"
        params_out = dict(frequency=freq, duration=duration)
        return (label, "event", params_out)

    @logger
    @interval_timer
    def play_ttls(self, verbose=False):
        """
        Play 'Twinkle Twinkle Little Star'.

        Args:
            verbose (bool, optional): Verbosity flag. If True, prints a message indicating the song is playing. Defaults to False.

        Returns:
            tuple: A tuple containing:
                - label (str): 'audio_alert_ttls'
                - category (str): 'event'
                - params_out (dict): Empty dictionary.
        """
        melody = [
            261.63,
            261.63,
            392.00,
            392.00,
            440.00,
            440.00,
            392.00,
            349.23,
            349.23,
            329.63,
            329.63,
            293.66,
            293.66,
            261.63,
        ]
        durations = np.array([1, 1, 1, 1, 1, 1, 2, 1, 1, 1, 1, 1, 1, 2]) * 0.25
        print("Playing twinkle twinkle little star :)") if verbose else None
        for note, duration in zip(melody, durations):
            self.play_tone(note, duration, verbose=False, log_enabled=False)
        return ("audio_alert_ttls", "event", {})

    @logger
    @interval_timer
    def play_synch(self, verbose=False):
        """
        Play a sequence of audio tones that can be used to synchronize an audio recording with the log.

        Args:
            verbose (bool, optional): Verbosity flag. If True, prints a message indicating the synchronization sound is playing. Defaults to False.

        Returns:
            tuple: A tuple containing:
                - label (str): 'audio_synch'
                - category (str): 'event'
                - params_out (dict): Empty dictionary.
        """
        print("Running audio synch sound") if verbose else None
        self.serial_port.serialObject.write("a".encode("utf-8"))
        self.serial_port.serialObject.write("s".encode("utf-8"))
        self.block_until_read()

        return ("audio_synch", "event", {})

    @logger
    @event_timer
    def start_recording(self, verbose=True, silent=True):
        """
        Start a recording by setting the record pin to high.
        Used in conjunction with "hardware trigger" in spikeglx.

        Args:
            verbose (bool, optional): Verbosity flag. If True, prints a message indicating the recording has started. Defaults to True.
            silent (bool, optional): If True, do not play an audio tone. Defaults to True.

        Returns:
            tuple: A tuple containing:
                - label (str): 'rec_start'
                - category (str): 'event'
                - params_out (dict): Empty dictionary.
        """
        if not silent:
            self.play_alert()
            print("Playing audio can disrupt the log timing")

        self.empty_read_buffer()
        self.rec_start_time = time.time()
        self.serial_port.serialObject.write("r".encode("utf-8"))
        self.serial_port.serialObject.write("b".encode("utf-8"))
        self.block_until_read()
        print("=" * 50 + "\nStarting recording!\n" + "=" * 50) if verbose else None
        return ("rec_start", "event", {})

    @logger
    @event_timer
    def stop_recording(self, verbose=True, reset_to_O2=False, silent=True):
        """
        Stop a recording by setting the record pin to low, and optionally reset the O2.
        Used in conjunction with "hardware trigger" in spikeglx.

        Args:
            verbose (bool, optional): Verbosity flag. If True, prints a message indicating the recording has stopped. Defaults to True.
            reset_to_O2 (bool, optional): If True, sets the O2 valve to open. Defaults to False.
            silent (bool, optional): If True, do not play an audio tone. Defaults to True.

        Returns:
            tuple: A tuple containing:
                - label (str): 'rec_stop'
                - category (str): 'event'
                - params_out (dict): Empty dictionary.
        """

        self.empty_read_buffer()
        self.serial_port.serialObject.write("r".encode("utf-8"))
        self.serial_port.serialObject.write("e".encode("utf-8"))
        self.block_until_read()
        self.rec_stop_time = time.time()
        print("=" * 50 + "\nStopping recording!\n" + "=" * 50) if verbose else None
        if not silent:
            self.play_alert()
            print("Playing audio can disrupt the log timing")

        if reset_to_O2:
            self.present_gas("O2", 1, verbose=False, progress=False)

        return ("rec_stop", "event", {})

    @logger
    @event_timer
    def start_camera_trig(self, fps=120, verbose=False):
        """
        Start the camera trigger by sending a serial command from the main experiment controller Teensy to the
        camera pulser Teensy. Set the camera frame rate.

        Args:
            fps (int, optional): Frames per second for the camera. Defaults to 120.
            verbose (bool, optional): Verbosity flag. If True, prints the frame rate. Defaults to False.

        Returns:
            tuple: A tuple containing:
                - label (str): 'start_camera'
                - category (str): 'event'
                - params_out (dict): Dictionary with 'fps' (frames per second).
        """
        self.serial_port.serialObject.write("a".encode("utf-8"))  # Auxiliary
        self.serial_port.serialObject.write("v".encode("utf-8"))  # Video
        self.serial_port.serialObject.write("b".encode("utf-8"))  # begin
        self.serial_port.write(int(fps), "uint8")
        print(f"Start camera trigger at {fps}fps") if verbose else None
        return ("start_camera", "event", {"fps": fps})

    @logger
    @event_timer
    def stop_camera_trig(self, verbose=False):
        """
        Stop the camera trigger by sending a serial command from the main experiment controller Teensy to the
        camera pulser Teensy.

        Args:
            verbose (bool, optional): Verbosity flag. If True, prints a message indicating the camera has stopped. Defaults to False.

        Returns:
            tuple: A tuple containing:
                - label (str): 'stop_camera'
                - category (str): 'event'
                - params_out (dict): Empty dictionary.
        """
        self.serial_port.serialObject.write("a".encode("utf-8"))  # Auxiliary
        self.serial_port.serialObject.write("v".encode("utf-8"))  # Video
        self.serial_port.serialObject.write("e".encode("utf-8"))  # end
        self.serial_port.write(int(0), "uint8")
        print(f"Stop camera") if verbose else None
        return ("stop_camera", "event", {})

    def block_until_read(self, verbose=False):
        """
        Wait to hear back from the teensy controller before continuing. This prevents multiple commands from
        being sent to the teensy and creating a backlog.
        """
        reply = []
        if verbose:
            print("Waiting for reply")
        while True:
            if self.serial_port.bytesAvailable() > 0:
                self.serial_port.read(1, "uint8")
                break

    def empty_read_buffer(self):
        """
        Clear any remaining serial messages
        """
        while self.serial_port.bytesAvailable() > 0:
            self.serial_port.serialObject.read()

    def reset(self):
        """
        Reset the experimental system by stopping the recordings, opening o2, and opening the heringbreuer valve.
        """
        self.stop_recording()
        self.open_valve(0)
        self.end_hb()
        # while self.serial_port.bytesAvailable()>0:
        #     self.serial_port.read(1,'byte')

    def _amp2int(self, amp):
        """
        Convert a float amplitude to an integer between 0 and 100.

        This method takes a float amplitude, clips it to be between 0 and 1, and scales it to an integer between 0 and 100.
        This is important to communicate to the Teensy controller, which expects an integer.

        Args:
            amp (float): Amplitude of the laser, a float between 0-1 (v).

        Returns:
            int: The amplitude scaled to an integer between 0 and 100.
        """
        amp = float(amp)
        if amp > 1:
            print(f"Amp was {amp}. Setting to 1")
            amp = 1
        elif amp < 0:
            print(f"Amp was {amp}. Setting to 0")
            amp = 0
        else:
            pass
        return int(amp * 100)

    def save_log(self, path=None, filename=None, verbose=True):
        """
        Save the log to a tab-separated file.

        Args:
            path (str or Path, optional): Path to save the log file. Defaults to the gate destination or D:/sglx_data.
            filename (str, optional): Filename to save the log as. Defaults to self.log_filename.
            verbose (bool, optional): Verbosity flag. If True, prints the save location. Defaults to True.

        Returns:
            None
        """
        path = self.gate_dest or path or Path(r"D:/sglx_data")
        now = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        filename = self.log_filename or filename
        if filename is None:
            print("NO LOG SAVED!!! NO filename is passed")
            return
        save_fn = path.joinpath(filename)
        log_df = pd.DataFrame(self.log)

        # make times relative to recording start
        base_time = self.rec_start_time or self.init_time

        log_df["start_time"] -= base_time
        log_df["end_time"] -= base_time

        # Make gasses extend until next gas change
        gasses = log_df.query('category=="gas"')
        end_times = np.concatenate(
            [gasses["start_time"][1:].values, [time.time() - base_time]]
        )
        gasses.iloc[:]["end_time"] = end_times
        log_df.loc[gasses.index] = gasses

        log_df.to_csv(save_fn, sep="\t")
        if verbose:
            print(f"Log saved to {save_fn}")

    @logger
    def make_log_entry(self, label, category, start_time=None, end_time=None, **kwargs):
        """
        Formats a custom log entry to be added to the log
        """
        start_time = time.time() or start_time
        end_time = np.nan or end_time
        output = dict(
            label=label,
            category=category,
            start_time=start_time,
            end_time=end_time,
            **kwargs,
        )
        return output

    @interval_timer
    def wait(self, wait_time_sec, msg=None, progress="bar"):
        """
        Pause the experiment for a predetermined amount of time.

        Args:
            wait_time_sec (float): Wait time in seconds.
            msg (str, optional): Custom message to print in the command line. Defaults to None.
            progress (str, optional): Type of progress indicator. Can be 'bar' for a progress bar or any other value for no progress indicator. Defaults to 'bar'.

        Returns:
            tuple: A tuple containing:
                - label (str): 'wait'
                - category (str): 'event'
                - params_out (dict): Empty dictionary.
        """
        try:
            msg = msg or "Waiting"
            start_time = time.time()
            update_step = 1
            if progress == "bar":
                pbar = tqdm(
                    total=int(wait_time_sec),
                    bar_format="{desc} Ctrl-c to skip. |{bar}{r_bar}",
                )
                pbar.set_description(msg)
                while get_elapsed_time(start_time) <= wait_time_sec:
                    time.sleep(update_step)
                    pbar.update(update_step)
                pbar.close()
            else:
                time.sleep(wait_time_sec)
        except KeyboardInterrupt:
            print('"Wait interrupted!')
            time.sleep(1)
            return ("wait", "event", {})

        return ("wait", "event", {})

    @interval_timer
    def settle(self, settle_time_sec=None, verbose=True, progress="bar"):
        """
        Convenience function to wait for the settle time, which can be passed or set as an object property.

        Args:
            settle_time_sec (float, optional): Settle time in seconds. If None, uses the object's `settle_time_sec` attribute. Defaults to None.
            verbose (bool, optional): Verbosity flag. If True, prints a message before and after settling. Defaults to True.
            progress (str, optional): Type of progress indicator. Can be 'bar' for a progress bar or any other value for no progress indicator. Defaults to 'bar'.

        Returns:
            tuple: A tuple containing:
                - label (str): 'probe_settle'
                - category (str): 'event'
                - params_out (dict): Empty dictionary.
        """
        if settle_time_sec is None:
            settle_time_sec = self.settle_time_sec
        msg = "Waiting for probe to settle"
        print(
            "MAKE SURE TO: \n\tENABLE THE RECORDING\n\tCHECK YOUR VALVES \n\tENABLE VIDEO \n\tAND PLACE THE OPTOFIBERS, IF REQUIRED"
        )
        self.play_alert()
        self.wait(settle_time_sec, msg=msg)
        print("Done settling") if verbose else None
        return ("probe_settle", "event", {})

    def plot_log(self):
        """
        Create a graphical representation of the expriment events.
        """
        log_df = pd.DataFrame(self.log)
        f = plt.figure(figsize=(12, 4))
        categories = log_df["category"].unique()
        for ii, cat in enumerate(categories):
            sub_df = log_df.query("category==@cat")
            for k, v in sub_df.iterrows():
                if np.isnan(v["end_time"]):
                    plt.vlines(v["start_time"], -0.25 + ii, 0.25 + ii, color="k")
                else:
                    plt.hlines(ii, v["start_time"], v["end_time"], lw=3)

                plt.text(v["start_time"], ii, v["label"], rotation=45)

        for ii, cat in enumerate(categories):
            plt.text(plt.gca().get_xlim()[0], ii, cat)

    def get_logname_from_user(self, verbose=True):
        """
        Prompt the user to input the gate destination, run name, gate number, and trigger number for logging purposes.

        Args:
            verbose (bool, optional): Verbosity flag. If True, prints the log save location. Defaults to True.

        Returns:
            None
        """
        self.gate_dest = input(
            f"Where is the gate being saved? (Default to {self.gate_dest_default})): "
        )
        if self.gate_dest == "":
            self.gate_dest = self.gate_dest_default
        while True:
            self.gate_dest = Path(self.gate_dest)
            if self.gate_dest.exists():
                break
            else:
                self.gate_dest = input("That folder does not exist.Try again... ")

        runname = input("what is the runname (from spikeglx)?: ")
        while True:
            try:
                gate_num = int(
                    input("what is the gate number (0,1,...)? Must be a number: ")
                )
                break
            except ValueError:
                print("Invalid input. Input must be a number")

        while True:
            try:
                trigger_num = int(
                    input("what is the trigger number (0,1,...)? Must be a number: ")
                )
                break
            except ValueError:
                print("Invalid input. Input must be a number")

        self.log_filename = (
            f"_cibbrig_log.table.{runname}.g{gate_num:0.0f}.t{trigger_num:0.0f}.tsv"
        )
        print(f"Log will save to {self.gate_dest}/{self.log_filename}")

    def get_laser_amp_from_user(self):
        """
        Prompt the user to input the laser power amplitude.

        This method continuously prompts the user to input a valid laser power amplitude between 0 and 1.
        It validates the input to ensure it is a float within the specified range.

        Returns:
            None
        """
        while True:
            val = input("Set the laser power (0-1)")
            try:
                val = float(val)
                if val < 0 or val > 1:
                    print("Invalid input. Must be between 0 and 1")
                else:
                    break
            except ValueError:
                print("Invalid input. Must be a number")
        self.laser_command_amp = val
        print(f"Laser amplitude set to {self.laser_command_amp}v")

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
                - category (str): 'odor'
                - params_out (dict): Dictionary with 'valve' key and the valve number as value.
        """
        self.serial_port.serialObject.write("s".encode("utf-8"))  # smell
        self.serial_port.serialObject.write("o".encode("utf-8"))  # open
        self.serial_port.write(int(valve), "uint8")

        print(f"Open olfactometer valve {valve}") if verbose else None
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
                - category (str): 'odor'
                - params_out (dict): Dictionary with 'valve' key and the valve number as value.
        """
        self.serial_port.serialObject.write("s".encode("utf-8"))  # smell
        self.serial_port.serialObject.write("c".encode("utf-8"))  # close
        self.serial_port.write(int(valve), "uint8")

        print(f"Close olfactometer valve {valve}") if verbose else None
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
        self.serial_port.serialObject.write("s".encode("utf-8"))  # smell
        self.serial_port.serialObject.write("b".encode("utf-8"))  # binary
        self.serial_port.write(decimal_value, "uint8")

        print(f"Set all valves to {binary_string}") if verbose else None
        self.block_until_read()
        return ("set_all_valves", "odor", {"valve": binary_string})

    @logger
    @interval_timer
    def present_odor(self, odor, duration_sec=None):
        """
        Present an odor by opening the corresponding olfactometer valve.

        This method uses the `odor_map` to find the valve number associated with the given odor and opens that valve.
        If a duration is specified, it waits for the specified duration and then switches back to the 'blank' odor.

        Args:
            odor (str): The name of the odor to present.
            duration_sec (float, optional): Duration in seconds to present the odor. If None, the odor is presented indefinitely. Defaults to None.

        Returns:
            tuple: A tuple containing:
                - label (str): 'present_odor'
                - category (str): 'odor'
                - params_out (dict): Dictionary with 'odor' key and the odor name as value.
        """
        print("This needs to be tested!!")
        if self.odormap is not None:
            valve_num = self.odor_map[odor]

        else:
            print("No odormap! Not changing olfactometer valves")
            return -1
        valve_string = "".join(["1" if ii == valve_num - 1 else "0" for ii in range(8)])
        self.set_all_olfactometer_valves(valve_string, log_enabled=False)
        if duration_sec is not None:
            time.sleep(duration_sec)
            valve_num = self.odor_map["blank"]
            valve_string = "".join(
                ["1" if ii == valve_num - 1 else "0" for ii in range(8)]
            )
            self.set_all_olfactometer_valves(valve_string, log_enabled=False)

        return ("present_odor", "odor", {"odor": odor})

    def graceful_close(self):
        self.close(self)

    def close(self):
        """
        Stop the recordings, close the camera trigger, and save the log.
        """
        self.stop_recording()
        print("Keyboard interrupted! Shutting down.")
        self.make_log_entry("Killed", "event")
        self.stop_camera_trig()
        self.save_log()

    def preroll(
        self, use_camera=True, gas="O2", settle_sec=None, set_olfactometer=False
    ):
        """
        Boilerplate commands to start an experiment.

        Asks the user for the logname and laser amplitude, then allows for probe settling.
        Sets the default laser amplitude.

        Args:
            use_camera (bool, optional): If True, starts the camera trigger. Defaults to True.
            gas (str, optional): The gas to send by default. Must be in the gas map: {'O2', 'room air', 'hypercapnia', 'hypoxia', 'N2'}. Defaults to 'O2'.
            settle_sec (float, optional): Settle time in seconds. If None, uses the default settle time for the controller object. Defaults to None.
            set_olfactometer (bool, optional): If True, sets the olfactometer valves. Defaults to False.

        Returns:
            None
        """
        if settle_sec is not None:
            self.settle_time_sec = settle_sec
        print(f"Default presenting {gas}")
        # self.stop_camera_trig()
        # self.stop_recording()

        # Assumes the first valve is blank
        if set_olfactometer:
            print('Initializing olfactometer. If the olfactometer is not connected, this will hang')
            if self.odor_map is None:
                print(
                    "WARNING! No odor map supplied. Olfactometer only works with supplied valve numbers"
                )
                self.set_all_olfactometer_valves("11111111")
                self.set_all_olfactometer_valves("00000000")
                self.set_all_olfactometer_valves("10000000")
            else:
                self.present_odor("blank")
        self.present_gas(gas)
        self.get_logname_from_user()
        self.get_laser_amp_from_user()
        self.settle()
        self.start_recording()
        if use_camera:
            time.sleep(0.5)
            self.start_camera_trig()


def sec2ms(val):
    """
    Convert a value from seconds to milliseconds and represent it as an integer.

    Args:
        val (float): The value in seconds to be converted.

    Returns:
        int: The value converted to milliseconds.
    """
    val = float(val)
    return int(val * 1000)


def get_elapsed_time(start_time):
    """
    Convenience function to compute the time that has elapsed since a given start time.

    Args:
        start_time (float): The start time in seconds since the epoch.

    Returns:
        float: The elapsed time in seconds.
    """
    curr_time = time.time()
    elapsed_time = curr_time - start_time
    return elapsed_time
