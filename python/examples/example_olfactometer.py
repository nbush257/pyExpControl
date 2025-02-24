
"""
This script demonstrates how to operate olfactometer valves
At the moment, the "present_odor" function is not implemented
Assumes SpikeGLX is running and gates and triggers are set to remote control
"""
import sys
sys.path.append('D:/pyExpControl/python')
from nebPod import Controller

PORT = 'COM11'
controller = Controller(PORT)
controller.preroll()
controller.present_gas('O2',60)

controller.open_olfactometer(2) # Open olfactometer valve 2
controller.wait(5) # Wait for 5 seconds
controller.close_olfactometer(2) # Close olfactometer valve 2


# Close all olfactometer valves except for valve 2
controller.set_all_olfactometer_valves('01000000')
controller.wait(5) # Wait for 5 seconds
# Close all olfactometer valves except for valve 1
controller.set_all_olfactometer_valves('10000000')

controller.wait(5) # Wait for 5 seconds
controller.set_all_olfactometer_valves('11111111') # Open all olfactometer valves
controller.wait(5) # Wait for 5 seconds
controller.set_all_olfactometer_valves('00000000') # Close all olfactometer valves
controller.wait(5) # Wait for 5 seconds

controller.stop_recording() # Stop recording

