# nebPod
This is a set of python and arduino code to control the NPX rig using serial communication. 
It is influenced by the Bpod control from Kepecs and Brody labs and uses the ArCOM package from Sanworks

Everything in the PYTHON folder is run on your local machine, can run in a mamba env, requires the installed dependencies, etc.

Everything in the TEENSY folder is going to be uploaded and run on your microcontroller (platformio recommended to set up your microcontroller)
The two will communicate with one another 

Installation
---
You will need to include the "digital_laser-control" and "Tbox" libraries (.cpp, .h) in your arduino framework so they can be referenced in the firmware sketch.
{You will need to clone the arcom repository discussed below. It's parent folder and the pyexpcontrol parent folder should be in the same directory. Otherwise some paths will break.}
Install dependencies
`pip install -r "D:\pyExpControl\python\requirements.txt"`
or wherever you put the pyExpControl directory

Also download the spikeglx-sdk from Bill Karsh: https://github.com/billkarsh/SpikeGLX-CPP-SDK, and copy the DLLs into the sglx pkg folder as instructed from those installation directions.
You will need to modify the nebPod.py file so that the spikeglx path points to that sglx_pkg folder. 
>[!NOTE]
>This is already done at JMB971

Usage
---
#### Usage for gui:
```
cd /path/to/nebPod/python
python nebPod-gui.py 
```

#### Usage for script:
```
cd /path/to/nebPod/python/scripts
python <your_script.py> 
```
Some example scripts are included.
Scripts will need to `sys.path.append(/path/to/ArCOM/Python3)` and `sys.path.append(/path/to/nebPod/python)` 

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
 - digital_laser-control 
    - Controls the analog out pin on the teensy to drive a digital_laser MLD laser. Ultimately all it does is provide a set of functions that time and scale an analog out signal in useful ways to control that laser (e.g., 0-1V outputs with pulses). Can be used in `B` (binary) or `S` (sigmoidal) mode. 
        - If binary, pulses are binary(i.e., digital) where LOW is 0v and HIGH is scaled between 0-1v to control the output power of the laser.
        - If sigmoidal, a smooth sigmoidal ramp over ~2ms is applied to the laser turning on or off to reduce light artifact on the NPX probe
 - teensy32_firmware
    - Handles pin mappings and serial communication from host PC to teensy3.2 microcontroller. Messages from python are:
        - `<command><subcommand><param1><param2>...`
        Where `command` and `subcommand` are characters.\
        Params are more flexible and may be multiple bytes as long as the sender and receiver agree.
