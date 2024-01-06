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
SETTLE_SEC = 3
EXPOSE_TIME = 0.01*60
INTERTRAIN_INTERVAL = 2
STIM_DURATION_INSP = 1
STIM_DURATION_EXP = 1

# Other parameters
BASE_AMP = 0.65
PHASIC_AMP = 0.65
N_STIMS = 1
N_TAG = 5
TAG_IPI = 1 # (s)
# doses = [2.5,2,1.5,1]
doses = [2.5,2]

# Where to save the log data
RUN_PATH = Path('D:/sglx_data')

# All things to run go in here. Need to pass the nebPod controller object to main.
def main(controller):

    # Keeping our logs seperate for now. Maybe want to join them later.
    log = [] 

    
    # Initialize with O2 - not logging here because isoflurane is a special experiment
    controller.present_gas('O2',1,verbose=True)
    # gas_log.append(controller.present_gas('O2',1,verbose=True))
    print(f'Set ISO to {doses[0]:.2f}%')
    
    # Let the probe settle
    nebPod.settle(SETTLE_SEC)

    # Start recording
    rec_start = controller.start_recording()
    rec_start_time = rec_start['start_time']
    log.append(rec_start)
    
    for dose in doses:    
        dose_name = f'iso_{dose:.2f}%'    
        print(dose_name)
        # Iso is not it's own functino because it is a special case
        iso_log = nebPod.make_log_entry(dose_name,'gas')
        log.append(iso_log)

        time.sleep(EXPOSE_TIME)
        log.append(controller.play_alert())

    log.append(controller.present_gas('hypercapnia',3,verbose=True))
    log.append(controller.present_gas('hypoxia',3,verbose=True))
    log.append(controller.present_gas('O2',3,verbose=True))


    log.append(controller.timed_hb(2,verbose=True))

    log.append(controller.play_tone(1000,3))
    log.append(controller.play_synch())

    # Test phasic stims
    for ii in range(N_STIMS):
        log.append(controller.phasic_stim('i','h',1,BASE_AMP,STIM_DURATION_INSP,INTERTRAIN_INTERVAL,freq=2,pulse_dur_sec=0.010,verbose=True))
    for ii in range(N_STIMS):
        log.append(controller.phasic_stim('e','h',1,BASE_AMP,STIM_DURATION_EXP,INTERTRAIN_INTERVAL,freq=2,pulse_dur_sec=0.010,verbose=True))

    for ii in range(N_STIMS):
        log.append(controller.phasic_stim('i','p',1,BASE_AMP,STIM_DURATION_INSP,INTERTRAIN_INTERVAL,freq=2,pulse_dur_sec=0.010,verbose=True))
    for ii in range(N_STIMS):
        log.append(controller.phasic_stim('e','p',1,BASE_AMP,STIM_DURATION_EXP,INTERTRAIN_INTERVAL,freq=2,pulse_dur_sec=0.010,verbose=True))

    for ii in range(N_STIMS):
        log.append(controller.phasic_stim('i','t',1,BASE_AMP,STIM_DURATION_INSP,INTERTRAIN_INTERVAL,freq=20,pulse_dur_sec=0.010,verbose=True))
    for ii in range(N_STIMS):
        log.append(controller.phasic_stim('e','t',1,BASE_AMP,STIM_DURATION_EXP,INTERTRAIN_INTERVAL,freq=20,pulse_dur_sec=0.010,verbose=True))

    # Test tagging
    log.append(controller.run_tagging(n=N_TAG,verbose=True,ipi_sec=TAG_IPI))
    log.append(controller.run_tagging(n=N_TAG,verbose=True,ipi_sec=TAG_IPI,pulse_dur_sec=0.02))
    

    # Test Pulse
    for stim_dur in [0.01,0.1,0.25]:
        for amp in [0.6,0.8,1]:
            log.append(controller.run_pulse(stim_dur,amp,verbose=True))
            time.sleep(1)
    
    # Test train
    for freq in [10,15,20]:
        for amp  in [0.6,0.8,1]:
            for pulse_dur in [0.01,0.02]:
                log.append(controller.run_train(2,freq,amp,pulse_dur,verbose=True))
                time.sleep(1)

    log.append(controller.stop_recording())

    log_df = pd.DataFrame(log)
    log_df['start_time'] -=rec_start_time
    log_df['end_time'] -=rec_start_time
    log_df.to_csv(RUN_PATH.joinpath('all_event_log.tsv'),sep='\t')


# Need to do this once the logging is figured out
# log,f = format_events(events,stims,rec_start_time)
if __name__=='__main__':
    controller = nebPod.Controller(PORT)
    try:
        main(controller)
    except KeyboardInterrupt:
        controller.close()
        

