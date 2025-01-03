# nebPod
This is a set of python and arduino code to control the NPX rig using serial communication. 
It is influenced by the Bpod control from Kepecs and Brody labs and uses the ArCOM package from Sanworks

You will need to include the "cobalt-control" and "Tbox" libraries (.cpp, .h) in your arduino framework so they can be referenced in the firmware sketch.

First, install dependencies
`pip install -r "D:\pyExpControl\python\requirements.txt"`
or wherever you put the pyExpControl directory

#### Usage for gui:
```
cd /path/to/nebPod/python
python nebPod-gui.py 
```

#### Usage for script:
```
cd /path/to/nebPod/python
python scripts/<your_script.py> 
```
Some example scripts are included

See the python-level readme for more info.



---
Teensy libraries
---

Must use a Teensy 3.2 as it has a true analog out pin.
Other microcontrollers with a real analog out (not PWM) can be used in theory.

### The teensy repository contains:
 - [ARCOM](https://github.com/sanworks/ArCOM) - Improvements to arduino Serial control by Sanworks 
 - Tbox
    - Teensybox, handles mostly deprecated pin mappings to control valves and experiments. Should be phased out but some functionality is still being used.
 - cobalt-control 
    - Controls the analog out pin on the teensy to drive a cobalt MLD laser. Ultimately all it does is provide a set of functions that time and scale an analog out signal in useful ways to control that laser (e.g., 0-1V outputs with pulses). Can be used in `B` (binary) or `S` (sigmoidal) mode. 
        - If binary, pulses are binary(i.e., digital) where LOW is 0v and HIGH is scaled between 0-1v to control the output power of the laser.
        - If sigmoidal, a smooth sigmoidal ramp over ~2ms is applied to the laser turning on or off to reduce light artifact on the NPX probe
 - teensy32_firmware
    - Handles pin mappings and serial communication from host PC to teensy3.2 microcontroller. Messages from python are:
        - `<command><subcommand><param1><param2>...`
        Where `command` and `subcommand` are characters.\
        Params are more flexible and may be multiple bytes as long as the sender and receiver agree.
