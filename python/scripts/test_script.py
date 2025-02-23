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

# pulse parameters
n_pulse_stims = 5
interpulse_interval = 5
pulse_dur = 0.01
# all things to run go in here. need to pass the nebpod controller object to main.

if __name__=='__main__':
    controller = Controller(PORT)

    # controller.preroll(settle_sec=2)
    # controller.wait(2)
    # controller.make_log_entry('Test log entry','event')
    # amps = controller.mW_to_volts([5,10,20,30])
    # for amp in amps:
    #     for ii in range(3):
    #         controller.run_pulse(0.1,amp,verbose=True)
    #         controller.wait(1)
    # controller.wait(2)
    # controller.stop_recording()

    controller.preroll(settle_sec=2,choose_laser_amps=True)
    controller.wait(2)
    controller.make_log_entry('Test log entry2','event')
    amps = controller.laser_command_amps
    controller.wait(10)
    controller.stop_recording()

    controller.wait(2)
    controller.preroll(settle_sec=2)
    controller.wait(2)
    controller.make_log_entry('Test log entry2','event')
    print(controller.laser_command_amps)
    controller.wait(2)
    controller.stop_recording()



