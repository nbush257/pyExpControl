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

    controller.preroll(settle_sec=2)
    controller.wait(2)
    amp = 0.65
    n = 5
    interval=3
    # controller.run_pulse(pulse_duration_sec=0.1,amp=amp,n=n,interval=interval,verbose=True)
    controller.run_pulse(pulse_duration_sec=0.1,amp=amp,verbose=True)
    controller.wait(10)
    controller.stop_recording()




