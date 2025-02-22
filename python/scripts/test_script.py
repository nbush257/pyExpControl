'''
Use this script to test all the functions in the experiment controller and as a template for new experiment protocols
NEB 2024-01-06

'''
import time
import sys
from pathlib import Path
import os
sys.path.append('D:/pyExpControl/python')
sys.path.append('D:/pyExpControl/ArCOM')
from nebPod import Controller
from pathlib import Path
import pandas as pd
try:
    from ArCOM import ArCOMObject 
except:
    print('No ARCOM. Just for debugging')

PORT = 'COM11'

# Time parameters in seconds
BASELINE_TIME = 4

# Pulse parameters
N_PULSE_STIMS = 5
INTERPULSE_INTERVAL = 5
PULSE_DUR = 0.01
# All things to run go in here. Need to pass the nebPod controller object to main.
def main(controller):
    pass

if __name__=='__main__':
    controller = Controller(PORT)
    controller.connect_to_spikeglx()


    # Write 3 gates [0,1,2]
    for ii in range(3):
        controller.start_recording()
        controller.wait(BASELINE_TIME)
        controller.make_log_entry('bob','event')
        controller.stop_recording()
        controller.wait(3)
    
    # Record gate 3 with multiple triggers
    controller.start_recording()
    controller.wait(BASELINE_TIME)
    controller.stop_recording()
    controller.wait(3)
    for ii in range(3):
        controller.start_recording(increment_gate=False)
        controller.wait(BASELINE_TIME)
        controller.make_log_entry('tom','event')
        controller.stop_recording()
        controller.wait(3)



