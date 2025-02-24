"""
This script demonstrates how to run multiple triggers for the same gate within a script
Assumes SpikeGLX is running and gates and triggers are set to remote control
"""
import sys
sys.path.append('D:/pyExpControl/python')
from nebPod import Controller

PORT = 'COM11'
controller = Controller(PORT)


# Record the first trigger
controller.preroll() 
controller.present_gas('O2',60) # Present O2 for 60 seconds
controller.stop_recording()

# Record the second trigger
controller.preroll(increment_gate=False,settle_sec=0) # We do not increment the gate nor need to settle the probe again
controller.present_gas('O2',60) # Present O2 for 60 seconds
controller.stop_recording()
