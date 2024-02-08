'''
Run experiment control for the TacCreCalcaFlpO Chrmine CreOnFlpOff experiments
1) Baseline
2) Phototag
3) CO2 exposure
4) Stimulation to evoke fast breathing
5) AUdio stim to evoke fast breathing

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
RA_SEC = 10*60
HC_SEC = 5*60

# Tagging parameters
TAG_IPI = 3 
TAG_PULSE_DUR = 0.1
TAG_AMP = 0.8
N_TAG = 75

# Entrainment protocol
N_ENTRAIN = 5 # Number per frequency
ENTRAIN_FREQS = [4,6,8,10,12,14]
ENTRAIN_DURATION = 15
ENTRAIN_ITI = 30
ENTRAIN_PULSE_DUR = 0.025
# Audio stim parameters
INTER_TONE_TIME = 30
TONE_FREQ = 1000
TONE_DUR = 0.5
N_AUDIO_STIMS = 10

# Where to save the log data
RUN_PATH = Path('D:/sglx_data')

def main(controller):
    controller.present_gas('room air',0.1)

    # Settle probe
    controller.settle(SETTLE_SEC)
    controller.start_recording()
    controller.wait(10)
    controller.start_camera_trig(fps=120,verbose=True)
    
    #Baseline recording
    controller.present_gas('room air',RA_SEC)

    # Audio Stims
    for _ in range(N_AUDIO_STIMS):
        controller.play_tone(TONE_FREQ,TONE_DUR)
        controller.wait(INTER_TONE_TIME)

    # Optotagging
    controller.run_tagging(n=N_TAG,verbose=True,ipi_sec=TAG_IPI,pulse_dur_sec=TAG_PULSE_DUR,amp=TAG_AMP)
    
    # Hypercapnia and recovery
    controller.present_gas('hypercapnia',HC_SEC)
    controller.present_gas('room air',5*60)
    
    #TODO: Stim for breathing
    for ff in ENTRAIN_FREQS:
        for ii in range(N_ENTRAIN):
            controller.run_train(duration_sec = ENTRAIN_DURATION, freq=ff,amp=TAG_AMP,pulse_dur_sec=ENTRAIN_PULSE_DUR)
            controller.wait(ENTRAIN_ITI,msg=f'Freq:{ff}, n={ii} of {N_ENTRAIN}')
    
    controller.stop_camera_trig(verbose=True)
    controller.wait(10)
    controller.stop_recording()
    controller.save_log()

if __name__=='__main__':
    controller = Controller(PORT)
    try:
        main(controller)
    except KeyboardInterrupt:
        controller.close()
        

