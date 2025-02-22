'''
Use this script to test all the functions in the experiment controller and as a template for new experiment protocols
NEB 2024-01-06

'''
#TODO: make simple and short
import time
import sys
from pathlib import Path
import os
curr_dir = Path(os.getcwd())
sys.path.append(str(curr_dir))
sys.path.append(str(curr_dir.parent.joinpath('ArCOM/Python3')))
from nebPod import Controller
from pathlib import Path
import pandas as pd
try:
    from ArCOM import ArCOMObject 
except:
    print('No ARCOM. Just for debugging')

PORT = 'COM11'

# Time parameters in seconds
BASELINE_TIME = 10

# Pulse parameters
N_PULSE_STIMS = 5
INTERPULSE_INTERVAL = 5
PULSE_DUR = 0.01

# All things to run go in here. Need to pass the nebPod controller object to main.
def main(controller):

    controller.preroll(gas='O2', use_camera=False, set_olfactometer=False,settle_sec=5)
    controller.present_gas('O2',BASELINE_TIME)
    amps = controller.laser_command_amps[0]

    # Pulses
    pulse_dur = PULSE_DUR
    for ii in range(N_PULSE_STIMS):
        controller.wait(INTERPULSE_INTERVAL,msg=f'Pulse {ii+1} of {N_PULSE_STIMS}; Duration: {pulse_dur}')
        controller.run_pulse(pulse_dur,amp,verbose=True)
    controller.play_ttls()

    # Stop recording
    controller.stop_recording()

    # Log events


if __name__=='__main__':
    controller = Controller(PORT)
    try:
        main(controller)
    except KeyboardInterrupt:
        controller.close()
        

