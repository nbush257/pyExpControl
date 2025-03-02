'''
Use this script to test all the functions in the experiment controller and as a template for new experiment protocols
NEB 2024-01-06

'''
import sys
sys.path.append('D:/pyExpControl/python')
from nebPod import Controller

PORT = 'COM11'


controller = Controller(PORT)

controller.settle(61)
controller.user_delay('Administer CNO 1mg/kg')
controller.present_gas('O2', 10)
print('bob')

