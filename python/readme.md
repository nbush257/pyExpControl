# Overview of `nebPod.py`

The `nebPod.py` file defines the `Controller` class, which is used to manage and control experiments using Teensy microcontrollers via serial communication. Inspired by Bpod, this class provides an  interface to control various aspects of the NPX rig, including gas presentation, laser control, and olfactometer valve management.

The `Controller` class can be used in two different ways: through a GUI or in a Python script.

## Usage

### Using the GUI

The GUI provides an interactive interface to control the NPX rig.

```sh
cd /path/to/nebPod/python
python nebPod_gui.py
```

## Using a Python Script (preferred)
You can write a Python script to automate the control of the NPX rig.

```
from nebPod import Controller
PORT = 'COM11'
controller = Controller(PORT)

# Preroll automatically interrogates user for recording details, waits for a predetermined settle time, and starts recording.
controller.preroll()

# Runs an optogenetic train for 5s at 10Hz and command amplitude 0.6v
controller.run_train(5,10,0.6)
controller.stop_recording()

```