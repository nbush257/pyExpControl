'''
Use this script to test all the functions in the experiment controller and as a template for new experiment protocols
NEB 2024-01-06
'''
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
SETTLE_SEC = 15*60 
BASELINE_TIME = 10*60

# Pulse parameters
N_PULSE_STIMS = 25
INTERPULSE_INTERVAL = 15

# Phasic parameters
INTERTRAIN_INTERVAL = 30 # 30 
STIM_DURATION_INSP = 10 #10
STIM_DURATION_EXP = 2 # 2
PULSE_DURATIONS = [0.01,0.05,0.5,1] 
EXP_PHASIC_TRAIN_FREQS = [5,10,25]
PHASIC_PULSE_DUR = 0.01
N_STIMS = 5

# Hering breuer parameters
N_HB = 10
HB_DURATION = 3

# All things to run go in here. Need to pass the nebPod controller object to main.
def main(controller):
    controller.get_logname_from_user()
    controller.get_laser_amp_from_user()
    AMP = controller.laser_command_amp

    controller.present_gas('O2',1,log_enabled=False,progress=False)    
    # Let the probe settle
    controller.settle(SETTLE_SEC)


    # Start recording
    controller.start_recording()
    controller.present_gas('O2',BASELINE_TIME)

    # Pulses
    for pulse_dur in PULSE_DURATIONS:
        for ii in range(N_PULSE_STIMS):
            controller.wait(INTERPULSE_INTERVAL,msg=f'Pulse {ii+1} of {N_PULSE_STIMS}; Duration: {pulse_dur}')
            controller.run_pulse(pulse_dur,AMP,verbose=True)

    # Phasic stims
    for ii in range(N_STIMS):
        controller.wait(INTERTRAIN_INTERVAL,msg=f'phasic stim {ii+1} of {N_STIMS}')
        controller.phasic_stim('i','h',1,AMP,STIM_DURATION_INSP,verbose=True)
    for ii in range(N_STIMS):
        controller.wait(INTERTRAIN_INTERVAL,msg=f'phasic stim {ii+1} of {N_STIMS}')
        controller.phasic_stim('e','h',1,AMP,STIM_DURATION_EXP,verbose=True)
    
    controller.wait(30)
    # Vary frequency in expiratory trains
    for freq in EXP_PHASIC_TRAIN_FREQS:
        for ii in range(N_STIMS):
            controller.phasic_stim('e','t',1,AMP,STIM_DURATION_EXP,freq = freq,pulse_duration_sec=PHASIC_PULSE_DUR,verbose=True)
            controller.wait(INTERTRAIN_INTERVAL)
    
    #Hering Breuers
    for ii in range(N_HB):
        controller.wait(INTERTRAIN_INTERVAL,msg=f'Hering Breuer {ii} of {N_HB}')
        controller.timed_hb(HB_DURATION,verbose=True)

    controller.play_ttls()

    # Stop recording
    controller.stop_recording()

    # Log events
    controller.save_log()


if __name__=='__main__':
    controller = Controller(PORT)
    try:
        main(controller)
    except KeyboardInterrupt:
        controller.close()
        

