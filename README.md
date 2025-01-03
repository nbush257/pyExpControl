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