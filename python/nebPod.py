# TODO: Camera control
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
import functools

def interval_timer(func):
    '''
    Decorator that appends the start and stop time to the output of a function
    Function must have three outputs:
    label: descriptor of the function call
    category: descriptor of the function category (e.g., opto, event,gas)
    params: dictionary of parameters that the function was called with
    '''

    def wrapper(*args, **kwargs):
        start_time = time.time()
        label,category,params = func(*args, **kwargs)
        end_time = time.time()

        output = dict(
            label=label,
            category=category,
            start_time=start_time,
            end_time = end_time,
            **params
        )
        return output
    return wrapper

def event_timer(func):
    '''
    Decorator that appends the start time to the output of a function
    Function must have three outputs:
    label: descriptor of the function call
    category: descriptor of the function category (e.g., opto, event,gas)
    params: dictionary of parameters that the function was called with    
    '''
    
    def wrapper(*args, **kwargs):
        start_time = time.time()
        label,category,params = func(*args, **kwargs)
        output = dict(
            label=label,
            category=category,
            start_time=start_time,
            end_time = np.nan,
            **params
        )
        return output
    return wrapper

def logger(func):
    '''
    Decorator that appends ouptut of a function call to the controllers "log" object. 
    '''
    def wrapper(self, *args, log_enabled=True,**kwargs):
        result = func(self, *args, **kwargs)
        if log_enabled:
            self.log.append(result)
            self.save_log(verbose=False)
        return result
    return wrapper

class Controller:
    def __init__(self,port,gas_map = None,cobalt_mode='S'):
        try:
            self.serial_port = ArCOMObject(port,115200)  # Replace 'COM11' with the actual port of your Arduino
            self.IS_CONNECTED=True
            print('Connected!')
        except:
            self.IS_CONNECTED = False
            print(f"No Serial port found on {port}. GUI will show up but not do anything")
        # Set the gas map if supplied. This maps the teensy pin to the gas 
        self.gas_map = gas_map or {0:'O2',1:'room air',2:'hypercapnia',3:'hypoxia',4:'N2'}
        self.ADC_RANGE=1023 # 10bit adc range (TODO: read from teeensy)
        self.V_REF = 3.3 # Teensy 3.2 vref
        self.MAX_MILLIWATTAGE = 310. # Thorlabs light meter max range to scale the photometer calibration
        self.settle_time_sec = 15*60 # Default settle time
        self.log = [] # Initialize the log list
        self.rec_start_time = None 
        self.rec_stop_time = None
        self.gate_dest = None
        self.gate_dest_default = 'D:/sglx_data'
        self.log_filename = None
        self.init_time = time.time()
        self.init_cobalt(null_voltage=0.4) # Initialize the laser controller object
        self.laser_command_amp = None
    
    @logger
    @event_timer
    def open_valve(self,valve_number,log_style=None):
        '''
        Open a valve by its pin number on the teensy. Closes all the others
        '''
        self.serial_port.serialObject.write('v'.encode('utf-8'))
        self.serial_port.write(valve_number,'uint8')
        self.block_until_read()
        # Write to log as either the gas presented or the valve number opened.
        if log_style=='gas':
            label=f'{self.gas_map[valve_number]}'
        else:
            label=f'open_valve_{int(valve_number)}'
        return(label,'gas',{})
    
    @logger
    @event_timer
    def present_gas(self,gas,presentation_time =None,verbose=False,progress='bar'):
        '''
        this is a blocking wrapper to open_valve that takes a gas name as input,
        and then sleeps the function for the presentation time
        gas - 'str'. must be a key in gasmap
        presentation time (s)

        '''
        assert gas in self.gas_map.values(), f'requested gas is not available. Must be :{self.gas_map.values()}'
        # invert the dictionary to use gas to map to the valve
        inv_map = {v: k for k, v in self.gas_map.items()}

        print(f'Presenting {gas}') if verbose else None
        self.open_valve(inv_map[gas],log_enabled=False)
        if presentation_time is not None:
            self.wait(presentation_time,msg=f'Presenting {gas}',progress=progress)
        return(f'present_{gas}','gas',{})
    
    @logger
    @event_timer
    def end_hb(self,verbose=False):
        '''
        End the hering breuer stimulation by reopening the hering breuer valve
        '''
        print('End hering breuer') if verbose else None
        self.serial_port.serialObject.write('h'.encode('utf-8'))
        self.serial_port.serialObject.write('e'.encode('utf-8'))
        self.block_until_read()

        return('end_heringbreuer','event',{})

    @logger
    @event_timer
    def start_hb(self,verbose=False):
        '''
        Start the hering breuer stimulation by closing the hering breuer valve
        '''
        print('start hering breuer') if verbose else None
        self.serial_port.serialObject.write('h'.encode('utf-8'))
        self.serial_port.serialObject.write('b'.encode('utf-8'))
        self.block_until_read()
        return('start_heringbreuer','event',{})
    
    @logger
    @interval_timer
    def timed_hb(self,duration,verbose=False):
        '''
        Start and end a hering breuer stimulation by wrapping to the hering breuer sub-processes
        '''
        print(f'Run hering breuer for {duration}s') if verbose else None

        self.start_hb(log_enabled=False)
        time.sleep(duration)
        self.end_hb(log_enabled=False)
        return('hering_breuer','event',{'duration':duration})
    
    @logger
    @event_timer
    def run_pulse(self,pulse_duration_sec,amp,verbose=False):
        '''
        Run a single opto pulse
        duration (float) : in s
        amp (float): in v (0-1)
        '''
        #  Convert to ms for arduino
        duration = sec2ms(pulse_duration_sec)
        print(f'Running opto pulse at {amp:.2f}V for {duration}ms') if verbose else None
        amp_int = self._amp2int(amp)
        self.serial_port.serialObject.write('p'.encode('utf-8'))
        self.serial_port.write(duration,'uint16')
        self.serial_port.write(amp_int,'uint8')
        self.block_until_read()

        label = 'opto_pulse'
        params_out = dict(
            amplitude=amp,
            duration=pulse_duration_sec
        )

        return(label,'opto',params_out)
    
    @logger
    @interval_timer
    def run_train(self,duration_sec,freq,amp,pulse_duration_sec,verbose=False):
        '''
        Run a train of opto pulses
        duration: (float)  - Full train duration (s)
        freq: (float) - Stim frequency (Hz)
        amp: (float) - range from 0-1
        pulse_dur: (float) pulse duration (s)
        '''
        #convert units
        duration = sec2ms(duration_sec)
        pulse_duration = sec2ms(pulse_duration_sec)

        print(f'Running opto train:\n\tAmplitude:{amp:.2f}V\n\tFrequency:{freq:.1f}Hz\n\tPulse duration:{pulse_duration}ms\n\tTrain duration:{duration_sec:.3f}s') if verbose else None

        self.empty_read_buffer()
        amp_int = self._amp2int(amp)
        self.serial_port.serialObject.write('t'.encode('utf-8'))
        self.serial_port.write(duration,'uint16')
        self.serial_port.write(freq,'uint8')
        self.serial_port.write(amp_int,'uint8')
        self.serial_port.write(pulse_duration,'uint8')
        self.block_until_read()

        label = 'opto_train'
        params_out = dict(
            amplitude = amp,
            duration=duration_sec,
            frequency = freq,
            pulse_duration=pulse_duration_sec
        )
        return(label,'opto',params_out)

    @logger
    @interval_timer
    def run_tagging(self,n=75,pulse_duration_sec=0.050,amp=1.0,ipi_sec=3,verbose=True):
        '''
        Run a preset train that is specific for opto-tagging. 

        n: number of tagging stims
        pulse_duration_sec: duration of stimualtion (s)
        amp: amplitude of stimulation (v, 0-1)
        ipi_sec: interpulse interval (s)

        '''
        pulse_duration_ms = sec2ms(pulse_duration_sec)

        if verbose:
            print('running opto tagging')
        self.empty_read_buffer()
        for ii in range(n):
            if verbose:
                print(f'\ttag {pulse_duration_ms}ms stim: {ii+1} of {n}. amp: {amp} ')
            self.run_pulse(pulse_duration_sec,amp,log_enabled=False)
            time.sleep(ipi_sec)
        
        label = 'opto_tagging'
        params_out = dict(
            n_tags = int(n),
            amplitude=amp,
            pulse_duration=pulse_duration_sec,
            interpulse_interval=ipi_sec
        )
        return(label,'opto',params_out)

    @logger
    @interval_timer
    def phasic_stim(self,phase,mode,n,amp,duration_sec,intertrain_interval_sec=30.0,freq=None,pulse_duration_sec=None,verbose=False):
        '''
        Run stimulations that are triggered from the diaphragm activity
        phase: ['e','i'] (Expiratory, Inspiratory) triggered stimulations
        mode: ['h','t','p'] ('hold','train','pulse') - hold is a solid stimulation. Train is a high-frequency train. Pulse is a single pulse.
        n : number of repititons
        amp: amplitude of stimulation (v, 0-1)
        duration_sec: duration of stimulation window (typically ~10 for inspiration, 2-4 for expiration)
        intertrain_interval_sec interval: time between stimulation windows
        freq: (optional) frequency of pulse train if using train mode
        pulse_duration_sec: (optional) Pulse duration if using "train" or "pulse" mode
        '''
        assert mode in ['h','t','p'], 'Stimulation mode {mode} not supported'
        assert phase in ['e','i'], 'Stimulation trigger {phase} not supported'

        phase_map = {'e':'exp','i':'insp'}
        mode_map = {'h':'hold','t':'train','p':'pulse'}


        # Handle the different modes
        if mode =='h':
            freq = None
            pulse_duration_sec = None
        if mode=='t':
            assert freq is not None, ' frequency is needed for phasic  trains'
            assert pulse_duration_sec is not None, 'pulse duration is needed for phasic  trains'
            pulse_dur_ms = sec2ms(pulse_duration_sec)
        if mode == 'p':
            assert pulse_duration_sec is not None, 'pulse duration is needed for phasic single pulses'
            pulse_dur_ms = sec2ms(pulse_duration_sec)
            freq = None
        if verbose:
            print(f'Running opto phasic stims:{phase_map[phase]},{mode_map[mode]},{freq=},{pulse_duration_sec=}')
        
        
        if n==1:
            intertrain_interval_sec=0.0

        intertrain_interval_ms = sec2ms(intertrain_interval_sec)
        duration_ms = sec2ms(duration_sec)

        self.empty_read_buffer()
        amp_int = self._amp2int(amp)
        self.serial_port.serialObject.write('a'.encode('utf-8'))
        self.serial_port.serialObject.write('p'.encode('utf-8'))
        self.serial_port.serialObject.write(phase.encode('utf-8'))
        self.serial_port.serialObject.write(mode.encode('utf-8'))
        self.serial_port.write(n,'uint8')
        self.serial_port.write(duration_ms,'uint16')
        self.serial_port.write(intertrain_interval_ms,'uint16')
        self.serial_port.write(amp_int,'uint8')
        if mode == 't':
            self.serial_port.write(pulse_dur_ms,'uint8')
            self.serial_port.write(int(freq),'uint8')
        
        if mode == 'p':
            self.serial_port.write(pulse_dur_ms,'uint8')

        self.block_until_read()

        label=f'opto_phasic'
        params_out = dict(
            phase=phase_map[phase],
            mode=mode_map[mode],
            amplitude=amp,
            duration=duration_sec,
            frequency = freq,
            pulse_duration=pulse_duration_sec
        )

        return(label,'opto',params_out)
    

    def poll_laser_power(self,amp,output='mw',verbose=False):
        '''
        Turn on the laser and read a voltage-in to measure the laser power
        amp: float between 0-1 (v)
        output: Units of output requested. Can be ['mw','v']. Otherwise it returns the raw read from the arduino
        '''
        amp_int = self._amp2int(amp)
        print(f'Testing amplitude: {amp}') if verbose else None
        self.serial_port.serialObject.write('o'.encode('utf-8'))
        self.serial_port.serialObject.write('p'.encode('utf-8'))
        self.serial_port.write(amp_int,'uint8')
        while self.serial_port.bytesAvailable()<2:
            time.sleep(0.001)
        power_int = self.serial_port.read(1,'uint16') # Power as a 10bit integer
        power_v = power_int/self.ADC_RANGE * self.V_REF # Powerr as a voltage
        power_mw = (power_v/2.)*self.MAX_MILLIWATTAGE # power in milliwatts
        self.block_until_read()

        if output=='v':
            return(power_v)
        elif output=='mw':
            return(power_mw)
        else:
            print('returning read digital bit val')
            return(power_int)

        
    def auto_calibrate(self,amp_range=None,amp_res=0.01,plot = False,output='mw',verbose=False):
        '''
        Automatically calibrate the laser by proceeding through a sequnce of command powers and reading the photometer output.
        amp_range: upper and lower limits of the voltage command to test
        amp_res: resolution of voltages to sample (i.e., step sizes)
        plot: If true, plot the relationship between the voltage command and the output.
        output: Units of output requested. Can be ['mw','v']. Otherwise it returns the raw read from the arduino
        '''
        amp_range = amp_range or [0,1.01]
        amps_to_test = np.arange(amp_range[0],amp_range[1],amp_res)
        # Add a zero to get background voltage
        amps_to_test = np.concatenate([[0],amps_to_test])

        # Initialize output
        powers = np.zeros_like(amps_to_test) * np.nan

        for ii,amp in enumerate(amps_to_test):
            power_mw = self.poll_laser_power(amp,verbose=verbose,output=output)
            powers[ii] = power_mw

        # Subtract off the first reading (NB: commenting out for now.)
        powers -=powers[0]
        if plot:
            f = plt.figure()
            plt.plot(amps_to_test[1:],powers[1:],'ko-')
            if output == 'mw':
                plt.ylabel('Power (mw)')
            else:
                plt.ylabel('Analog voltage read')
            plt.axhline(powers[0],color='r',ls='--')
            
            plt.xlabel('Command voltage (V)')
            plt.tight_layout()
            plt.show()

        return(amps_to_test,powers)
    

    def set_max_milliwattage(self,val):
        '''
        Set the range for calibrating. This value is read out from the thorlabs light 
        meter and converts the voltage output from thorlabs to milliwatts
        '''
        self.MAX_MILLIWATTAGE = val

    def turn_on_laser(self,amp,verbose=False):
        '''
        Turn on the laser. 
        '''
        print(f'Turning on laser at amp: {amp}') if verbose else None
        amp_int = self._amp2int(amp)
        self.serial_port.serialObject.write('o'.encode('utf-8'))
        self.serial_port.serialObject.write('o'.encode('utf-8'))
        self.serial_port.write(amp_int,'uint8')
        self.block_until_read()
    

    def turn_off_laser(self,amp,verbose=False):
        '''
        Turn off the laser
        '''
        print(f'Turning off laser from amp: {amp}') if verbose else None
        amp_int = self._amp2int(amp)
        self.serial_port.serialObject.write('o'.encode('utf-8'))
        self.serial_port.serialObject.write('x'.encode('utf-8'))
        self.serial_port.write(amp_int,'uint8')
        self.block_until_read()

    @logger
    @interval_timer
    def play_tone(self,freq,duration_sec,verbose=False):
        '''
        Flexibly play an audio tone
        Frequency in Hz (float)
        Duration in s (int)
        '''
        self.empty_read_buffer()
        duration_ms = sec2ms(duration_sec)
        print(f'Playing audio tone: frequency{freq}, duration:{duration_sec:.3f} (s)') if verbose else None
        self.serial_port.serialObject.write('aa'.encode('utf-8'))
        self.serial_port.write(int(freq),'uint16')
        self.serial_port.write(int(duration_ms),'uint16')
        self.block_until_read()

        label='tone'
        params_out = dict(
            frequency=freq,
            duration=duration_sec
        )
        return(label,'event',params_out)

    @logger
    @interval_timer
    def play_alert(self,verbose=False):
        '''
        Play a predefined audio tone. Used to alert the user.
        '''
        freq=1000
        duration=0.500
        self.play_tone(freq,duration,verbose=verbose,log_enabled=False)
        
        label = 'audio_alert'
        params_out = dict(
            frequency=freq,
            duration=duration
        )
        return(label,'event',params_out)


    @logger
    @interval_timer
    def play_ttls(self,verbose=False):
        '''
        Play twinkle twinkle little star. 
        '''
        melody = [
            261.63, 261.63, 392.00, 392.00, 440.00, 440.00, 392.00,
            349.23, 349.23, 329.63, 329.63, 293.66, 293.66, 261.63
        ]
        durations = np.array([1,1,1,1,1,1,2,1,1,1,1,1,1,2])*0.25
        print('Playing twinkle twinkle little star :)') if verbose else None
        for note,duration in zip(melody,durations):
            self.play_tone(note,duration,verbose=False,log_enabled=False)
        return('audio_alert_ttls','event',{})
        
    @logger
    @interval_timer
    def play_synch(self,verbose=False):
        '''
        Play a sequence of audio tones that can be used to synchronize an audio recording with the log.
        '''
        print('Running audio synch sound') if verbose else None
        self.serial_port.serialObject.write('a'.encode('utf-8'))
        self.serial_port.serialObject.write('s'.encode('utf-8'))
        self.block_until_read()

        return('audio_synch','event',{})
    
    @logger
    @event_timer
    def start_recording(self,verbose=True,silent=True):
        '''
        Start a recording by setting the record pin to high. 
        Used in conjunction with "hardware trigger" in spikeglx.

        silent - if true, do not play an audio tone.
        '''
        if not silent:
            self.play_alert()
            print('Playing audio can disrupt the log timing')

        self.empty_read_buffer()
        self.rec_start_time = time.time()
        self.serial_port.serialObject.write('r'.encode('utf-8'))
        self.serial_port.serialObject.write('b'.encode('utf-8'))
        self.block_until_read()
        print('='*50+'\nStarting recording!\n'+'='*50) if verbose else None
        return('rec_start','event',{})

    @logger
    @event_timer
    def stop_recording(self,verbose=True,reset_to_O2=False,silent=True):
        '''
        Stop a recording by setting the record pin to low, and optionally reset the O2 
        Used in conjunction with "hardware trigger" in spikeglx.

        silent - if true, do not play an audio tone.
        reset_to_O2: Sets the O2 valve to open.
        '''
            
        self.empty_read_buffer()
        self.serial_port.serialObject.write('r'.encode('utf-8'))
        self.serial_port.serialObject.write('e'.encode('utf-8'))
        self.block_until_read()
        self.rec_stop_time=time.time()
        print('='*50+'\nStopping recording!\n'+'='*50) if verbose else None
        if not silent:
            self.play_alert()
            print('Playing audio can disrupt the log timing')

        if reset_to_O2:
            self.present_gas('O2',1,verbose=False,progress=False)

        return('rec_stop','event',{})


    @logger
    @event_timer
    def start_camera_trig(self,fps=120,verbose=False):
        '''
        Start the camera trigger by sending a serial command from the main experiment controller teensy to the 
        camera pulser teensy. Set the camera frame rate.
        '''
        self.serial_port.serialObject.write('a'.encode('utf-8')) # Auxiliary
        self.serial_port.serialObject.write('v'.encode('utf-8')) # Video 
        self.serial_port.serialObject.write('b'.encode('utf-8')) # begin
        self.serial_port.write(int(fps),'uint8')
        print(f'Start camera trigger at {fps}fps') if verbose else None
        return('start_camera','event',{'fps':fps})
    
    @logger
    @event_timer
    def stop_camera_trig(self,verbose=False):
        '''
        Stop the camera trigger by sending a serial command from the main experiment controller teensy to the 
        camera pulser teensy.
        '''
        self.serial_port.serialObject.write('a'.encode('utf-8')) # Auxiliary
        self.serial_port.serialObject.write('v'.encode('utf-8')) # Video 
        self.serial_port.serialObject.write('e'.encode('utf-8')) # begin
        self.serial_port.write(int(0),'uint8')  
        print(f'Stop camera') if verbose else None
        return('stop_camera','event',{})

    def block_until_read(self,verbose=False):
        '''
        Wait to hear back from the teensy controller before continuing. This prevents multiple commands from 
        being sent to the teensy and creating a backlog.
        '''
        reply = []
        if verbose:
            print('Waiting for reply')
        while True:
            if self.serial_port.bytesAvailable()>0:
                self.serial_port.read(1,'uint8')
                break

    def empty_read_buffer(self):
        '''
        Clear any remaining serial messages
        '''
        while self.serial_port.bytesAvailable()>0:
            self.serial_port.serialObject.read()

    def reset(self):
        '''
        Reset the experimental system by stopping the recordings, opening o2, and opening the heringbreuer valve.
        '''
        self.stop_recording()
        self.open_valve(0)
        self.end_hb()
        # while self.serial_port.bytesAvailable()>0:
        #     self.serial_port.read(1,'byte')
    
    
    def _amp2int(self,amp):
        '''
        Takes in a float amplitude, clips it to between 0-1 and scales it to 
        an integer between 0-100
        '''
        amp = float(amp)
        if amp>1:
            print(f'Amp was {amp}. Setting to 1')
            amp=1
        elif amp<0:
            print(f'Amp was {amp}. Setting to 0')
            amp=0
        else:
            pass
        return(int(amp*100))
    
    def save_log(self,path = None,filename=None,verbose=True):
        '''
        Save log to a tab seperated file
        path: path to save to. Defaults to D:/sglx)data
        filename: filename to save to. Defaults to "all_event_log_<YYYY-MM-DD-HH-mm-ss>.tsv
        make_relative: subtracts the recording onset time.
        '''
        path = self.gate_dest or path or Path(r'D:/sglx_data') 
        now = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        filename = self.log_filename or filename
        if filename is None:
            print('NO LOG SAVED!!! NO filename is passed')
            return
        save_fn = path.joinpath(filename)
        log_df = pd.DataFrame(self.log)
        
        # make times relative to recording start
        base_time = self.rec_start_time or self.init_time

        log_df['start_time'] -=base_time
        log_df['end_time'] -=base_time
        
        # Make gasses extend until next gas change
        gasses = log_df.query('category=="gas"')
        end_times = np.concatenate([gasses['start_time'][1:].values,[time.time()-base_time]])
        gasses.iloc[:]['end_time'] = end_times
        log_df.loc[gasses.index] = gasses

        log_df.to_csv(save_fn,sep='\t')
        if verbose:
            print(f'Log saved to {save_fn}')
    
    @logger
    def make_log_entry(self,label,category,start_time = None,end_time = None,**kwargs):
        '''
        Formats a custom log entry
        '''
        start_time = time.time() or start_time
        end_time = np.nan or end_time
        output=dict(
            label=label,
            category=category,
            start_time=start_time,
            end_time=end_time,
            **kwargs)
        return(output)
    
    @interval_timer
    def wait(self,wait_time_sec,msg=None,progress='bar'):
        '''
        Pause the experiment for a predetermined amount of time.
        wait_time_sec: wait time in seconds
        msg: custom message to print in the command line
        progress can be: 'bar' (would be fun to have a animation)
        '''
        try:
            msg = msg or 'Waiting'
            start_time = time.time()
            update_step=1
            if progress == 'bar':
                pbar = tqdm(total=int(wait_time_sec),bar_format='{desc} Ctrl-c to skip. |{bar}{r_bar}')
                pbar.set_description(msg)
                while get_elapsed_time(start_time)<=wait_time_sec:
                    time.sleep(update_step)
                    pbar.update(update_step)
                pbar.close()
            else:
                time.sleep(wait_time_sec)
        except KeyboardInterrupt:
            print('"Wait interrupted!')
            time.sleep(1)
            return('wait','event',{})

        return('wait','event',{})
    
    @interval_timer
    def settle(self,settle_time_sec=None,verbose=True,progress='bar'):
        '''
        Convinience function to wait for the settle time which can be passed or set as a object property
        '''
        if settle_time_sec is None:
            settle_time_sec = self.settle_time_sec
        msg = 'Waiting for probe to settle'
        print('MAKE SURE TO ENABLE THE RECORDING, CHECK YOUR VALVES, AND PLACE THE OPTOFIBERS, IF REQUIRED')
        self.play_alert()
        self.wait(settle_time_sec,msg=msg)
        print('Done settling') if verbose else None
        return('probe_settle','event',{})
    

    def init_cobalt(self,mode ='S',power_meter_pin =16,null_voltage = 0.5,verbose=False):
        '''
        Use this to initialize or modify the cobalt object in the arduino. Particularly useful if you want to switch between sigmoidal andz
        '''
        #TODO: test null voltage modification
        null_voltage_uint8 = int(255*null_voltage)
        self.serial_port.serialObject.write('c'.encode('utf-8'))
        self.serial_port.serialObject.write('m'.encode('utf-8'))
        self.serial_port.serialObject.write(mode.encode('utf-8'))
        self.serial_port.write(power_meter_pin,'uint8')
        self.serial_port.write(null_voltage_uint8,'uint8')
        self.block_until_read()
        print(f'initialized cobalt with mode {mode} and power meter pin {power_meter_pin}') if verbose else None


    def plot_log(self):
        '''
        Create a graphical representation of the expriment events.
        '''
        log_df = pd.DataFrame(self.log)
        f = plt.figure(figsize=(12,4))
        categories = log_df['category'].unique()
        for ii,cat in enumerate(categories):
            sub_df = log_df.query('category==@cat')
            for k,v in sub_df.iterrows():
                if np.isnan(v['end_time']):
                    plt.vlines(v['start_time'],-0.25+ii,0.25+ii,color='k')
                else:
                    plt.hlines(ii, v['start_time'],v['end_time'],lw=3)
                
                plt.text(v['start_time'],ii,v['label'],rotation=45)

        for ii,cat in enumerate(categories):    
            plt.text(plt.gca().get_xlim()[0],ii,cat)
    
    
    def get_logname_from_user(self,verbose=True):
        self.gate_dest = input(f'Where is the gate being saved? (Default to {self.gate_dest_default})): ')
        if self.gate_dest=='':
            self.gate_dest = self.gate_dest_default
        while True:
            self.gate_dest = Path(self.gate_dest)
            if self.gate_dest.exists():
                break
            else:
                self.gate_dest = input('That folder does not exist.Try again... ')

        runname = input('what is the runname (from spikeglx)?: ')
        while True:
            try:
                gate_num = int(input('what is the gate number (0,1,...)? Must be a number: '))
                break
            except ValueError:
                print('Invalid input. Input must be a number')

        while True:
            try:
                trigger_num = int(input('what is the trigger number (0,1,...)? Must be a number: '))
                break
            except ValueError:
                print('Invalid input. Input must be a number')
    
    
        self.log_filename = f'_cibbrig_log.table.{runname}.g{gate_num:0.0f}.t{trigger_num:0.0f}.tsv'
        print(f"Log will save to {self.gate_dest}/{self.log_filename}")


    def get_laser_amp_from_user(self):
        while True:
            val = input('Set the laser power (0-1)')
            try:
                val = float(val)
                if val<0 or val>1:
                    print('Invalid input. Must be between 0 and 1')
                else:
                    break
            except ValueError:
                print('Invalid input. Must be a number')
        self.laser_command_amp = val
        print(f'Laser amplitude set to {self.laser_command_amp}v')

    @logger
    @event_timer
    def open_olfactometer(self,valve,verbose=True):
        '''
        Open an olfactometer valve
        '''
        self.serial_port.serialObject.write('s'.encode('utf-8')) #smell
        self.serial_port.serialObject.write('o'.encode('utf-8')) #open
        self.serial_port.write(int(valve),'uint8')

        print(f'Open olfactometer valve {valve}') if verbose else None
        self.block_until_read()
        return('open_olfactometer_valve','odor',{'valve':valve})

    @logger
    @event_timer
    def close_olfactometer(self,valve,verbose=True):
        '''
        Close an olfactometer valve
        '''
        self.serial_port.serialObject.write('s'.encode('utf-8')) #smell
        self.serial_port.serialObject.write('c'.encode('utf-8')) #close
        self.serial_port.write(int(valve),'uint8')

        print(f'Close olfactometer valve {valve}') if verbose else None
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
        self.serial_port.serialObject.write('s'.encode('utf-8')) #open
        self.serial_port.serialObject.write('b'.encode('utf-8')) #open
        self.serial_port.write(decimal_value,'uint8')

        print(f'Set all valves to {binary_string}') if verbose else None
        self.block_until_read()
        return('set_all_valves','odor',{'valve':binary_string})

    def graceful_close(self):
        self.close(self)

    def close(self):
        self.stop_recording()
        print("Keyboard interrupted! Shutting down.")
        self.make_log_entry('Killed','event')
        self.stop_camera_trig()
        self.save_log()
    
    def preroll(self,use_camera=True,gas='O2',settle_sec=None):
        """
        Boilerplate commands to start an experiment.
        Sets the default laser amplitude.

        Args:
            use_camera (bool, optional): If true, starts the camera trigger. Defaults to True.
            gas (str, optional): Which gas to send by default. Defaults to 'O2'.must be in gas map: {'O2','room air','hypercapnia','hypoxia','N2'} 
            settle_sec (_type_, optional): Settle time n seconds. Defaults to None which grabs the default for the controller object
        """        
        '''
        '''
        self.settle_time_sec = settle_sec or self.settle_time_sec
        print(f'Default presenting {gas}')
        self.present_gas(gas)
        self.get_logname_from_user()
        self.get_laser_amp_from_user()
        self.settle()
        self.start_recording()
        if use_camera:
            self.start_camera_trig()
        

        
def sec2ms(val):
    '''
    convert a value from  seconds to milliseconds 
    and represent it as an int
    '''
    val = float(val)
    return(int(val*1000))  

def get_elapsed_time(start_time):
    '''
    Convinience function to compute the time that has elapsed since a given time
    '''
    curr_time = time.time()
    elapsed_time = curr_time-start_time
    return(elapsed_time)

