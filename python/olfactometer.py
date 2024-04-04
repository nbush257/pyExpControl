# TODO: extend and test functionality with thorlabs LED drivers (long term)
import os
import sys
from pathlib import Path
curr_dir = Path(os.getcwd())
sys.path.append(str(curr_dir))
sys.path.append(str(curr_dir.parent.joinpath('ArCOM/Python3')))
from ArCOM import ArCOMObject 
import time
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pathlib import Path
from tqdm import tqdm
import datetime

from nebPod import event_timer,interval_timer,logger,Controller


class Olfactometer(Controller):
    def __init__(self,port):
        super().__init__(port)
        self.set_all_olfactometer_valves('00000000')

    @logger
    @event_timer
    def open_olfactometer(self,valve,verbose=True):
        '''
        Open an olfactometer valve
        '''
        self.serial_port.serialObject.write('o'.encode('utf-8')) #open
        self.serial_port.write(int(valve),'uint8')

        print(f'Opens olfactometer valve {valve}') if verbose else None
        self.block_until_read()
        return('open_olfactometer_valve','odor',{'valve':valve})

    @logger
    @event_timer
    def close_olfactometer(self,valve,verbose=True):
        '''
        Close an olfactometer valve
        '''
        self.serial_port.serialObject.write('c'.encode('utf-8')) #close
        self.serial_port.write(int(valve),'uint8')

        print(f'Closes olfactometer valve {valve}') if verbose else None
        self.block_until_read()
        return('close_olfactometer_valve','odor',{'valve':valve})
    
    @logger
    @event_timer
    def set_all_olfactometer_valves(self,binary_string,verbose=True):
        """Set all valves of the olfactometer witha  single command. 
        Pass a binary string (e.g., '01010101') Where 0 is closed and 1 is open

        Pass a string that looks like the olfactometer(left most bit is the left most valve). 
        Reverses the string before sending due to bit ordering (there is probably a better way to do this but I am ignorant)

        Input:
        Valve 8 is the right most bit, Valve 1 is the left most bit.
        
        Send to teensy:
        Valve 1 is the right most bit, Valve 8 is the left most bit.
        
        Args:
            binary_string (str): Binary string
            verbose (bool, optional): _description_. Defaults to True.
        """        
        assert(len(binary_string)==8),'Binary string must be 8 characters long.'
        binary_string_revr = binary_string[::-1]
        decimal_value = int(binary_string_revr, 2)
        self.serial_port.serialObject.write('b'.encode('utf-8')) #open
        self.serial_port.write(decimal_value,'uint8')

        print(f'Sets all valves to {binary_string}') if verbose else None
        self.block_until_read()
        return('set_all_valves','odor',{'valve':binary_string})



