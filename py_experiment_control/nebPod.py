# TODO: Camera control
# TODO: extend and test functionality with thorlabs LED drivers (long term)
# TODO: allow to run in non-sigmoidal mode

from ArCOM import ArCOMObject 
import serial
import time
import matplotlib.pyplot as plt
import numpy as np
import datetime
import threading
import seaborn as sns
import pandas as pd
from pathlib import Path

def interval_timer(func):
    '''
    appends the start and stop time to the output of the function 
    '''
    def wrapper(*args, **kwargs):
        start_time = time.time()
        label,category,params = func(*args, **kwargs)
        end_time = time.time()
        # This only allows functinos with three outputs
        # MAKE THIS A DICT OUTPUT
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
    appends the start time to the output of a function. Also returns nan as the end time
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
        # This only allows functinos with three outputs
        return output

    return wrapper

def logger(func):
    def wrapper(self, *args, log_enabled=True,**kwargs):
        result = func(self, *args, **kwargs)
        if log_enabled:
            self.log.append(result)
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
        # Set the gas map if supplied
        self.gas_map = gas_map or {0:'O2',1:'room air',2:'hypercapnia',3:'hypoxia',4:'N2'}
        self.ADC_RANGE=1023 # 10bit adc range (TODO: read from teeensy)
        self.V_REF = 3.3 # Teensy 3.3 vref
        self.MAX_MILLIWATTAGE = 500. # TODO: Get from thorlabs lightmeter
        self.settle_time_sec = 15*60
        self.log = []
        self.rec_start_time = None
        self.rec_stop_time = None
        self.init_cobalt()
    
    @logger
    @event_timer
    def open_valve(self,valve_number):
        start_time = time.time()
        self.serial_port.serialObject.write('v'.encode('utf-8'))
        self.serial_port.write(valve_number,'uint8')
        self.block_until_read()

        label=f'open_valve_{int(valve_number)}'
        return(label,'gas',{})
    
    @logger
    @event_timer
    def present_gas(self,gas,presentation_time = 5.0,verbose=False,progress='bar'):
        '''
        this is a blocking wrapper to open_valve that takes a gas name as input,
        and then sleeps the function for the presentation time
        gas - 'str'. must be a key in gasmap
        presentation time (s)

        '''
        assert gas in self.gas_map.values(), f'requested gas is not available. Must be :{self.gas_map.values()}'
        # invert the dictionary to use gas to map to the valve
        inv_map = {v: k for k, v in self.gas_map.items()}

        print(f'Presenting {gas} for {presentation_time}s') if verbose else None
        self.open_valve(inv_map[gas],log_enabled=False)
        self.wait(presentation_time,msg=f'Presenting {gas}',progress=progress)
        return(f'present_{gas}','gas',{})
    
    @logger
    @event_timer
    def end_hb(self,verbose=False):
        print('End hering breuer') if verbose else None
        self.serial_port.serialObject.write('h'.encode('utf-8'))
        self.serial_port.serialObject.write('e'.encode('utf-8'))
        self.block_until_read()

        return('end_heringbreuer','event',{})

    @logger
    @event_timer
    def start_hb(self,verbose=False):
        print('start hering breuer') if verbose else None
        self.serial_port.serialObject.write('h'.encode('utf-8'))
        self.serial_port.serialObject.write('b'.encode('utf-8'))
        self.block_until_read()
        return('start_heringbreuer','event',{})
    
    @logger
    @interval_timer
    def timed_hb(self,duration,verbose=False):
        print(f'Run hering breuer for {duration}s') if verbose else None

        self.start_hb(log_enabled=False)
        time.sleep(duration)
        self.end_hb(log_enabled=False)
        return('hering_breuer','event',{'duration':duration})
    
    @logger
    @event_timer
    def run_pulse(self,duration_sec,amp,verbose=False):
        '''
        duration: in s
        amp: in v (0-1)
        '''
        #  Convert to ms for arduino
        duration = sec2ms(duration_sec)
        print(f'Running opto pulse at {amp:.2f}V for {duration}ms') if verbose else None
        amp_int = self._amp2int(amp)
        self.serial_port.serialObject.write('p'.encode('utf-8'))
        self.serial_port.write(duration,'uint16')
        self.serial_port.write(amp_int,'uint8')
        self.block_until_read()

        label = 'opto_pulse'
        params_out = dict(
            amplitude=amp,
            duration=duration_sec
        )

        return(label,'opto',params_out)
    
    @logger
    @interval_timer
    def run_train(self,duration_sec,freq,amp,pulse_dur_sec,verbose=False):
        '''
        duration: (float)  - Full train duration (s)
        freq: (float) - Stim frequency (Hz)
        amp: (float) - range from 0-1
        pulse_dur: (float) pulse duration (s)
        '''
        #convert units
        duration = sec2ms(duration_sec)
        pulse_dur = sec2ms(pulse_dur_sec)

        print(f'Running opto train:\n\tAmplitude:{amp:.2f}V\n\tFrequency:{freq:.1f}Hz\n\tPulse duration:{pulse_dur}ms\n\tTrain duration:{duration_sec:.3f}s') if verbose else None

        self.empty_read_buffer()
        amp_int = self._amp2int(amp)
        self.serial_port.serialObject.write('t'.encode('utf-8'))
        self.serial_port.write(duration,'uint16')
        self.serial_port.write(freq,'uint8')
        self.serial_port.write(amp_int,'uint8')
        self.serial_port.write(pulse_dur,'uint8')
        self.block_until_read()

        label = 'opto_train'
        params_out = dict(
            amplitude = amp,
            duration=duration_sec,
            frequency = freq,
            pulse_duration=pulse_dur_sec
        )
        return(label,'opto',params_out)

    @logger
    @interval_timer
    def run_tagging(self,n=75,pulse_dur_sec=0.010,amp=1.0,ipi_sec=3,verbose=True):
        '''
        n: number of tagging stims
        duration: duration of stimualtion (s)
        ipi: interpulse interval (s)
        amp: amplitude of stimulation (v, 0-1)
        '''
        pulse_duration_ms = sec2ms(pulse_dur_sec)

        if verbose:
            print('running opto tagging')
        self.empty_read_buffer()
        for ii in range(n):
            if verbose:
                print(f'\ttag {pulse_duration_ms}ms stim: {ii+1} of {n}. amp: {amp} ')
            self.run_pulse(pulse_dur_sec,amp,log_enabled=False)
            time.sleep(ipi_sec)
        # self.block_until_read()
        
        label = 'opto_tagging'
        params_out = dict(
            n_tags = int(n),
            amplitude=amp,
            pulse_duration=pulse_dur_sec,
            interpulse_interval=ipi_sec
        )
        return(label,'opto',params_out)

    @logger
    @interval_timer
    def phasic_stim(self,phase,mode,n,amp,duration_sec,intertrain_interval_sec=0.0,freq=None,pulse_dur_sec=None,verbose=False):
        '''
        mode: 'e','i','t','p' (expiration,inspiration,trains,pulses)
        n : number of repititons
        amp: amplitude of stimulation (between 0 and 1)
        duration: duration of stimulation (typically ~10 for inspiration, 2-4 for expiration)
        intertrain interval: time between trains
        '''
        assert mode in ['h','t','p'], 'Stimulation mode {mode} not supported'
        assert phase in ['e','i'], 'Stimulation mode {mode} not supported'

        phase_map = {'e':'exp','i':'insp'}
        mode_map = {'h':'hold','t':'train','p':'pulse'}


        # Handle the difference modes
        if mode =='h':
            freq = None
            pulse_dur_sec = None
        if mode=='t':
            assert freq is not None, ' frequency is needed for phasic  trains'
            assert pulse_dur_sec is not None, 'pulse duration is needed for phasic  trains'
            pulse_dur_ms = sec2ms(pulse_dur_sec)
        if mode == 'p':
            assert pulse_dur_sec is not None, 'pulse duration is needed for phasic single pulses'
            pulse_dur_ms = sec2ms(pulse_dur_sec)
            freq = None
        if verbose:
            print(f'Running opto phasic stims:{phase_map[phase]},{mode_map[mode]}')
            # print(f'\tAmplitude:{amp:.2f}V\n\tFrequency:{freq:.1f}Hz\n\tPulse duration:{pulse_dur_ms}ms\n\tTrain duration:{duration_sec:.3f}s') if verbose else None
        
        
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
            pulse_duration=pulse_dur_sec
        )

        return(label,'opto',params_out)
    

    def poll_laser_power(self,amp,verbose=False,output='mw'):
        '''
        amp: float between 0-1 (v)
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
        power_mw = (power_v/2)/self.MAX_MILLIWATTAGE # power in milliwatts
        self.block_until_read()

        if output=='v':
            return(power_v)
        elif output=='mw':
            return(power_mw)
        else:
            print('returning read voltage')
            return(power_mw)

        
    def auto_calibrate(self,amp_range=None,amp_res=0.01,plot = False,output='mw',verbose=False):
        amp_range = amp_range or [0.5,1.01]
        amps_to_test = np.arange(amp_range[0],amp_range[1],amp_res)
        # Add a zero to get background voltage
        amps_to_test = np.concatenate([[0],amps_to_test])

        powers = np.zeros_like(amps_to_test) * np.nan

        for ii,amp in enumerate(amps_to_test):
            power_mw = self.poll_laser_power(amp,verbose=verbose,output=output)
            powers[ii] = power_mw

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


    def turn_on_laser(self,amp,verbose=False):
        print(f'Turning on laser at amp: {amp}') if verbose else None
        amp_int = self._amp2int(amp)
        self.serial_port.serialObject.write('o'.encode('utf-8'))
        self.serial_port.serialObject.write('o'.encode('utf-8'))
        self.serial_port.write(amp_int,'uint8')
        self.block_until_read()
    

    def turn_off_laser(self,amp,verbose=False):
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
        print('Running audio synch sound') if verbose else None
        self.serial_port.serialObject.write('a'.encode('utf-8'))
        self.serial_port.serialObject.write('s'.encode('utf-8'))
        self.block_until_read()

        return('audio_synch','event',{})
    
    @logger
    @event_timer
    def start_recording(self,verbose=True,silent=False):
        self.play_alert() if not silent else None
        self.empty_read_buffer()
        self.rec_start_time = time.time()
        self.serial_port.serialObject.write('r'.encode('utf-8'))
        self.serial_port.serialObject.write('b'.encode('utf-8'))
        self.block_until_read()
        print('='*50+'\nStarting recording!\n'+'='*50) if verbose else None
        return('rec_start','event',{})

    @logger
    @event_timer
    def stop_recording(self,verbose=True,reset_to_O2=True,silent=False):
        self.empty_read_buffer()
        self.serial_port.serialObject.write('r'.encode('utf-8'))
        self.serial_port.serialObject.write('e'.encode('utf-8'))
        self.block_until_read()
        self.rec_stop_time=time.time()
        print('='*50+'\nStopping recording!\n'+'='*50) if verbose else None
        self.play_alert() if not silent else None

        if reset_to_O2:
            self.present_gas('O2',1,verbose=False,progress=False)

        return('rec_stop','event',{})


    @logger
    @event_timer
    def start_camera_trig(self,fps=120,verbose=False):
        #TODO: make a user determined framerate
        # print(f'Starting camera at {fps}') if verbose else None
        pass
        # return('start_camera','event',{'fps':fps})
    
    @logger
    @event_timer
    def stop_camera_trig(self):
        # print(f'Stopping camera') if verbose else None
        pass
        # return('stop_camera','event',{})

    def block_until_read(self,verbose=False):
        reply = []
        if verbose:
            print('Waiting for reply')
        while True:
            if self.serial_port.bytesAvailable()>0:
                self.serial_port.read(1,'uint8')
                break

    def empty_read_buffer(self):
        while self.serial_port.bytesAvailable()>0:
            self.serial_port.serialObject.read()

    def reset(self):
        self.stop_recording()
        self.open_valve(0)
        self.end_hb()
        # while self.serial_port.bytesAvailable()>0:
        #     self.serial_port.read(1,'byte')
    
    
    def close(self):
        self.reset()
        print('Closing experiment')
    
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
    
    def save_log(self,path = None,filename=None,make_relative=True,verbose=True):
        '''
        Save log to a file
        '''
        path = path or Path(r'D:/sglx_data') 
        filename = filename or 'all_event_log.tsv'
        save_fn = path.joinpath(filename)
        log_df = pd.DataFrame(self.log)
        
        # make times relative to recording start
        if make_relative:
            log_df['start_time'] -=self.rec_start_time
            log_df['end_time'] -=self.rec_start_time
        
        log_df.to_csv(save_fn,sep='\t')
        print(f'Log saved to {save_fn}')

    @logger
    def make_log_entry(self,label,category,start_time = None,end_time = None,**kwargs):
        '''
        Formats information that is needed for a log entry
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
        progress can be: 'bar' (would be fun to have a animation)
        '''
        msg = msg or 'Waiting'
        start_time = time.time()
        update_step=1
        try:
            if progress == 'bar':
                from tqdm import tqdm
                pbar = tqdm(total=int(wait_time_sec),bar_format='{desc}: |{bar}{r_bar}')
                pbar.set_description(msg)
                while get_elapsed_time(start_time)<=wait_time_sec:
                    time.sleep(update_step)
                    pbar.update(update_step)
                pbar.close()
            else:
                time.sleep(wait_time_sec)
        except:
            print('Progress ui not supported. Need to install TQDM')
        return('wait','event',{})
    
    @interval_timer
    def settle(self,settle_time_sec=None,verbose=True,progress='bar'):
        if settle_time_sec is None:
            settle_time_sec = self.settle_time_sec
        msg = 'Waiting for probe to settle'
        self.wait(settle_time_sec,msg=msg)
        print('Done settling') if verbose else None
        return('probe_settle','event',{})
    

    def init_cobalt(self,mode ='S',power_meter_pin =16,verbose=False):
        '''
        Use this to initialize or modify the cobalt object in the arduino. Particularly useful if you want to switch between sigmoidal and binary modes
        '''
        self.serial_port.serialObject.write('c'.encode('utf-8'))
        self.serial_port.serialObject.write('m'.encode('utf-8'))
        self.serial_port.serialObject.write(mode.encode('utf-8'))
        self.serial_port.write(power_meter_pin,'uint8')
        self.block_until_read()
        print(f'initialized cobalt with mode {mode} and power meter pin {power_meter_pin}') if verbose else None

def sec2ms(val):
    '''
    convert a value from  seconds to milliseconds 
    and represent it as an int
    '''
    val = float(val)
    return(int(val*1000))  








def get_elapsed_time(start_time):
    curr_time = time.time()
    elapsed_time = curr_time-start_time
    return(elapsed_time)


def plot_events(df):
    '''
    df whould be either a intervals or times dataframe
    '''
    pass

def plot_events(events,stims,recording_start,plot=True):
    # TODO FINISH LOGGING
    # TODO: standardize for ALF
    event_log = pd.DataFrame(events,columns=['event','absolute_time'])
    stim_log = pd.DataFrame(stims,columns=['stim_epochs','absolute_time'])
    event_log['t0'] = event_log['absolute_time'] - recording_start
    stim_log['t0'] = stim_log['absolute_time'] - recording_start

    if plot:
        f = plt.figure()
        for ii in range(0,event_log.shape[0]):
            t0 = event_log.loc[ii,'t0']
            if ii>=log.shape[0]-1:
                tf = t0
            else:
                tf = event_log.loc[ii+1,'t0']
            evt = event_log.loc[ii,'event']
            plt.hlines(0,t0,tf,lw=10,color=plt.cm.Dark2_r(ii/10))
            plt.axvline(t0,color='k',ls=':')
            plt.text(t0,0.05,evt,ha='left',va='bottom',rotation=45)

        for ii in range(0,stim_log.shape[0]):
            t0 = stim_log.loc[ii,'t0']
            if ii>=stim_log.shape[0]-1:
                tf = t0
            else:
                tf = stim_log.loc[ii+1,'t0']
            evt = stim_log.loc[ii,'stim_epochs']
            plt.hlines(-0.2,t0,tf,lw=10,color=plt.cm.Dark2_r(ii/10))
            plt.axvline(t0,color='k',ls=':')
            plt.text(t0,-0.2,evt,ha='left',va='bottom',rotation=-45)
        plt.ylim(-0.5,0.5)
        sns.despine(left=True)
        plt.xlabel('Time (s)')
        plt.yticks([])
        plt.tight_layout()
        plt.show()
    return(log,f)


