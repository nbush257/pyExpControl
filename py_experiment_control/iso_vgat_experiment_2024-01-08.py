'''
Use this script to test all the functions in the experiment controller and as a template for new experiment protocols
NEB 2024-01-06
'''
try:
    from ArCOM import ArCOMObject 
except:
    print('No ARCOM. Just for debugging')
import time
import nebPod
from pathlib import Path
import pandas as pd

PORT = 'COM11'

# Time parameters in seconds
SETTLE_SEC = 0*60 
EXPOSE_TIME = 0.1*60
INTERTRAIN_INTERVAL = 1
STIM_DURATION_INSP = 1
STIM_DURATION_EXP = 1

# Other parameters
PHASIC_AMP = 0.65
N_STIMS = 1
N_TAG = 75
TAG_IPI = 3 # (s)
doses = [2.5,2,1.5,1]

# Where to save the log data
RUN_PATH = Path('D:/sglx_data')

# All things to run go in here. Need to pass the nebPod controller object to main.
def main(controller):

    # Keeping our logs seperate for now. Maybe want to join them later.

    # Initialize with O2 - not logging here because isoflurane is a special experiment
    controller.present_gas('O2',1,log_enabled=False,progress=False)
    # gas_log.append(controller.present_gas('O2',1,verbose=True))
    print(f'Set ISO to {doses[0]:.2f}%')
    
    # Let the probe settle
    controller.settle(SETTLE_SEC)


    # Start recording
    controller.start_recording()

    
    for dose in doses:    
        dose_name = f'iso_{dose:.2f}%'    
        # Iso is not it's own functino because it is a special case
        controller.make_log_entry(dose_name,'gas')
        controller.wait(EXPOSE_TIME,msg=dose_name)

            # Test phasic stims
        for ii in range(N_STIMS):
            controller.phasic_stim('i','h',1,PHASIC_AMP,STIM_DURATION_INSP,verbose=True)
            controller.wait(INTERTRAIN_INTERVAL,progress=False)
        for ii in range(N_STIMS):
            controller.phasic_stim('e','h',1,PHASIC_AMP,STIM_DURATION_EXP,verbose=True)
            controller.wait(INTERTRAIN_INTERVAL,progress=False)


        controller.play_ttls()

    # Stop recording
    controller.stop_recording()

    # Log events
    controller.save_log(path=RUN_PATH)


if __name__=='__main__':
    controller = nebPod.Controller(PORT)
    try:
        main(controller)
    except KeyboardInterrupt:
        controller.close()
        

