
"""
This script demonstrates how to operate olfactometer valves
At the moment, the "present_odor" function is not implemented
Assumes SpikeGLX is running and gates and triggers are set to remote control
"""
import sys
sys.path.append('D:/pyExpControl/python')
from nebPod import Controller

odor_map = {0:"H20",1:'nh3'}
PORT = 'COM11'
controller = Controller(PORT)
controller.odor_map = odor_map
controller.preroll(settle_sec=5,set_olfactometer=True,skip_opto_calibration=True)
controller.present_gas('O2',2)

controller.open_olfactometer(2) # Open olfactometer valve 2
controller.wait(5) # Wait for 5 seconds
controller.close_olfactometer(2) # Close olfactometer valve 2
controller.wait(5)


# Close all olfactometer valves except for valve 2
controller.set_all_olfactometer_valves('00001000')
controller.wait(5) # Wait for 5 seconds
# Close all olfactometer valves except for valve 1
controller.set_all_olfactometer_valves('10000000')


controller.present_odor('nh3',5) # Present odor 'nh3' for 5 seconds
controller.wait(4)

controller.stop_recording() # Stop recording

