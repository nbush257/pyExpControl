'''
Use this script to test all the functions in the experiment controller and as a template for new experiment protocols
NEB 2024-01-06

'''
import sys
sys.path.append('D:/pyExpControl/python')
from nebPod import Controller

PORT = 'COM11'


controller = Controller(PORT)
controller.settle(5)
controller.start_recording()
controller.laser_pulse_gpio(n=5,interval=3)
controller.run_pulse(pulse_duration_sec=0.5,amp=0.65,n=3,interval=2)
controller.stop_recording()

