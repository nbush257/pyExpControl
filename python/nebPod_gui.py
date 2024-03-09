#TODO: add connection, port choosing, reconnection button
import sys
import subprocess
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QGridLayout, QPushButton, QGroupBox, QLineEdit, QFileDialog, QLabel, QButtonGroup, QDial,QDialog,QCheckBox,QComboBox,QRadioButton,QHBoxLayout,QFrame
from PyQt5.QtGui import QPixmap, QDoubleValidator, QIntValidator, QIcon
from PyQt5.QtCore import Qt
import time
import matplotlib.pyplot as plt
import numpy as np
import os
from pathlib import Path
import datetime
import pandas as pd
import json
curr_dir = Path(os.getcwd())
sys.path.append(str(curr_dir))
sys.path.append(str(curr_dir.parent.joinpath('ArCOM/Python3')))
from ArCOM import ArCOMObject # Import ArCOMObject
import nebPod
try:
    import qdarktheme
    HAS_STYLING = True
except:
    HAS_STYLING = False
        
PORT = 'COM11'
class ArduinoController(QWidget):
    def __init__(self):
        super().__init__()

        # Set up ArCOM communication with Arduino
        try:
            self.controller = nebPod.Controller(PORT)
            self.IS_CONNECTED=True
        except:
            self.IS_CONNECTED = False
            print(f"No Serial port found on {PORT}. GUI will show up but not do anything")
        self.port = PORT
        self.laser_amp = 0.65
        self.null_voltage = 0.5
        self.cobalt_mode='S'
        self.hb_time = 0.5
        self.train_freq = 10.0
        self.train_duration  = 1.0
        self.train_pulse_dur = .025 
        self.gas_map = self.controller.gas_map
        self.insp_phasic_duration = 10.0
        self.exp_phasic_duration = 4.0
        self.save_path = Path('D:/')
        self.script_filename = None
        self.implemented_wavelengths = ['473nm','635nm','undefined']
        self.powermeter_lims = {'473nm':310.,'635nm':140.}
        self.implemented_fibers = ['200um doric 0.22NA','600um doric 0.22NA','undefined']
        self.fiber=self.implemented_fibers[0]
        self.light_wavelength=self.implemented_wavelengths[0]

        self.controller.init_cobalt(mode=self.cobalt_mode,null_voltage=self.null_voltage)
        self.end_hb()
        self.open_valve(0)
        self.init_ui()

    def init_ui(self):
        # Create layout
        main_layout = QGridLayout(self)
        main_layout.setAlignment(Qt.AlignTop)

        # Create file input field and button spanning the width
        file_layout = QVBoxLayout()
        self.file_path_input = QLineEdit(self)
        self.file_path_input.setPlaceholderText(str(self.save_path))
        self.file_path_input.setMinimumHeight(40)  # Set a larger height
        browse_button = QPushButton("Choose save path...", self)
        browse_button.clicked.connect(self.browse_directory)

        script_dialog = QVBoxLayout()
        self.script_path_input = QLineEdit(self)
        browse_script_button = QPushButton("Choose script to run", self)
        browse_script_button.clicked.connect(self.browse_script)


        file_layout.addWidget(self.file_path_input)
        file_layout.addWidget(browse_button)
        script_dialog.addWidget(self.script_path_input)
        script_dialog.addWidget(browse_script_button)

        script_run = QVBoxLayout()
        self.script_run_button = QPushButton('RUN SCRIPT',self)
        self.script_run_button.setStyleSheet('background-color: #4496c2')
        self.script_run_button.clicked.connect(self.run_script)
        script_run.addWidget(self.script_run_button)

        main_layout.addLayout(file_layout, 0, 0)
        main_layout.addLayout(script_dialog, 0, 1)
        main_layout.addLayout(script_run, 0, 2)
        # Create box for connecting:
        connect_box = QGridLayout()
        port_label = QLabel('COM Port:')
        port_lineedit = QLineEdit(self)
        port_lineedit.setPlaceholderText(PORT)
        port_connect_button = QPushButton('Connect COM')
        port_connect_button.clicked.connect(self.connect)

        port_disconnect_button = QPushButton('Disconnect COM')
        port_disconnect_button.clicked.connect(self.disconnect)
        connect_box.addWidget(port_label,0,0)
        connect_box.addWidget(port_lineedit,0,1)
        connect_box.addWidget(port_connect_button,1,0,1,2)
        connect_box.addWidget(port_disconnect_button,2,0,1,2)

        main_layout.addLayout(connect_box,0,3)

        # Create group box for toggle buttons (Valves)
        group_box_toggle = QGroupBox("Manual Valve Control", self)
        toggle_layout = QGridLayout(group_box_toggle)
        toggle_layout.setAlignment(Qt.AlignTop)

        # Create toggle buttons
        button_group = QButtonGroup(self)
        button_index = 0
        for row in range(4):
            for col in range(2):
                if button_index>4:
                    break
                toggle_button = QPushButton(self.gas_map[button_index], self)
                toggle_button.setCheckable(True)
                button_group.addButton(toggle_button, button_index)
                toggle_button.clicked.connect(lambda state, button_number=button_index: self.open_valve(button_number))
                toggle_layout.addWidget(toggle_button, row, col)
                button_index += 1
        
        # Create Hering breuer group
        hb_group = QGroupBox("Hering breuer", self)
        hb_lo = QGridLayout(hb_group)
        hb_lo.setAlignment(Qt.AlignTop)
        
        self.hb_label_text = QLabel('Hering Breuer timed interval (s):')
        self.hb_time_lineedit = QLineEdit()
        self.hb_time_lineedit.setText(f'{self.hb_time:.2f}')
        self.hb_time_lineedit.setValidator(QDoubleValidator(0.0,10.0,2))
        self.hb_time_lineedit.textChanged.connect(self.update_hb_time)

        self.hering_breuer_manual = QPushButton('Hering Breuer manual', self)
        self.hering_breuer_manual.pressed.connect(self.start_hb)
        self.hering_breuer_manual.released.connect(self.end_hb)
        
        self.hering_breuer_timed = QPushButton('Hering Breuer timed', self)
        self.hering_breuer_timed.clicked.connect(self.timed_hb)

        hb_lo.addWidget(self.hb_label_text,0,0)
        hb_lo.addWidget(self.hb_time_lineedit,0,1)
        hb_lo.addWidget(self.hering_breuer_manual,1,0)
        hb_lo.addWidget(self.hering_breuer_timed,1,1)

        main_layout.addWidget(group_box_toggle, 1, 0)
        main_layout.addWidget(hb_group, 2, 0)

        # Create group box for pulse duration buttons (Pulses)
           
        group_box_pulse = QGroupBox("Predefined pulses", self)
        pulse_layout = QGridLayout(group_box_pulse)
        pulse_layout.setAlignment(Qt.AlignTop)

        # Predefined pulses
        pulse_10ms_button = QPushButton("10ms Pulse", self)
        pulse_10ms_button.clicked.connect(lambda: self.run_pulse(0.01))

        pulse_50ms_button = QPushButton("50ms Pulse", self)
        pulse_50ms_button.clicked.connect(lambda: self.run_pulse(0.05))

        pulse_100ms_button = QPushButton("100ms Pulse", self)
        pulse_100ms_button.clicked.connect(lambda: self.run_pulse(0.100))

        pulse_200ms_button = QPushButton("200ms Pulse", self)
        pulse_200ms_button.clicked.connect(lambda: self.run_pulse(0.200))

        pulse_500ms_button = QPushButton("500ms Pulse", self)
        pulse_500ms_button.clicked.connect(lambda: self.run_pulse(0.500))
        
        pulse_1000ms_button = QPushButton("1000ms Pulse", self)
        pulse_1000ms_button.clicked.connect(lambda: self.run_pulse(1))

                
        hold_on_laser = QPushButton("Hold laser", self)
        hold_on_laser.pressed.connect(self.laser_on)
        hold_on_laser.released.connect(self.laser_off)

        pulse_layout.addWidget(pulse_10ms_button, 1, 0)
        pulse_layout.addWidget(pulse_50ms_button, 1, 1)
        pulse_layout.addWidget(pulse_100ms_button, 1, 2)
        pulse_layout.addWidget(pulse_200ms_button, 2, 0)
        pulse_layout.addWidget(pulse_500ms_button, 2, 1)
        pulse_layout.addWidget(pulse_1000ms_button, 2, 2)
        pulse_layout.addWidget(hold_on_laser, 3, 1)

        main_layout.addWidget(group_box_pulse, 2, 1)


        # Custom pulses
        group_box_stim_params = QGroupBox("Custom pulse train", self)
        stim_params_layout = QGridLayout(group_box_stim_params)
        stim_params_layout.setAlignment(Qt.AlignTop)

        # Freq
        train_freq_label = QLabel('Train frequency (0-40 Hz)')
        self.train_freq_lineedit = QLineEdit()
        self.train_freq_lineedit.setText(f'{self.train_freq:.0f}')
        self.train_freq_lineedit.setValidator(QDoubleValidator(0.0,40,0))
        self.train_freq_lineedit.textChanged.connect(self.update_train_freq)
        # Train duration
        train_dur_label = QLabel('Train duration (0s-30s)')
        self.train_dur_lineedit = QLineEdit()
        self.train_dur_lineedit.setText(f'{self.train_duration:.0f}')
        self.train_dur_lineedit.setValidator(QDoubleValidator(0.0,30.0,1))
        self.train_dur_lineedit.textChanged.connect(self.update_train_duration)
        # Pulse duration
        train_pulse_dur_label = QLabel('Pulse duration (ms)')
        self.pulse_dur_lineedit = QLineEdit()
        self.pulse_dur_lineedit.setText(f'{1000*self.train_pulse_dur:.0f}')
        self.pulse_dur_lineedit.setValidator(QIntValidator(0,1000))
        self.pulse_dur_lineedit.textChanged.connect(self.update_train_pulse_dur)
        # Laser amplitude
        amp_label_text = QLabel('Laser Amp (0-1v):')
        self.laser_amp_lineedit = QLineEdit()
        self.laser_amp_lineedit.setText(f'{self.laser_amp:.2f}')
        self.laser_amp_lineedit.setValidator(QDoubleValidator(0.0,1.0,2))
        self.laser_amp_lineedit.textChanged.connect(self.update_laser_amplitude_from_lineedit)
        self.laser_amp_dial = QDial()
        self.laser_amp_dial.setRange(0, 100)
        self.laser_amp_dial.setValue(int(self.laser_amp*100))
        self.laser_amp_dial.valueChanged.connect(self.update_laser_amplitude_from_dial)

        # Run train button
        train_button = QPushButton('Run custom train',self)
        train_button.clicked.connect(self.run_custom_train)

        # Visualize train button
        viz_train_button = QPushButton('Visualize custom train',self)
        viz_train_button.clicked.connect(self.viz_custom_train)

        # Create a horizontal line
        h_line = QFrame()
        h_line.setFrameShape(QFrame.HLine)
        h_line.setFrameShadow(QFrame.Sunken)

        # Set up a vertical layout
        line_box = QVBoxLayout()
        line_box.addWidget(h_line)

        # Set the layout for the main window

        # Change null voltage
        self.null_voltage_label = QLabel('Null voltage (0-1v)')
        self.null_voltage_linedit = QLineEdit()
        self.null_voltage_linedit.setText(f'{self.null_voltage}')
        self.null_voltage_linedit.setValidator(QDoubleValidator(0.0,1.0,2))
        self.null_voltage_linedit.textChanged.connect(self.update_null_voltage)
        

        #Change cobalt mode:
        mode_label = QLabel('Select laser mode:')
        self.binary_radio = QRadioButton('Binary')
        self.sigmoidal_radio = QRadioButton('Sigmoidal')
        self.sigmoidal_radio.setChecked(True)

        # Create a button group to make the radio buttons mutually exclusive
        self.button_group = QButtonGroup()
        self.button_group.addButton(self.binary_radio)
        self.button_group.addButton(self.sigmoidal_radio)
        self.binary_radio.toggled.connect(self.update_cobalt_mode)
        self.sigmoidal_radio.toggled.connect(self.update_cobalt_mode)
        mode_box = QHBoxLayout()
        mode_box.addWidget(mode_label)
        mode_box.addWidget(self.binary_radio)
        mode_box.addWidget(self.sigmoidal_radio)


        # Layout
        stim_params_layout.addWidget(train_freq_label, 1, 0)  
        stim_params_layout.addWidget(train_dur_label, 2, 0)  
        stim_params_layout.addWidget(train_pulse_dur_label, 3, 0)  
        stim_params_layout.addWidget(amp_label_text, 4, 0)

        stim_params_layout.addWidget(self.train_freq_lineedit,1,1)
        stim_params_layout.addWidget(self.train_dur_lineedit,2,1)
        stim_params_layout.addWidget(self.pulse_dur_lineedit,3,1)
        stim_params_layout.addWidget(self.laser_amp_lineedit, 4, 1)

        stim_params_layout.addWidget(self.laser_amp_dial,4, 2, 2, 2)
        
        stim_params_layout.addWidget(train_button, 5, 0)
        stim_params_layout.addWidget(viz_train_button, 5, 1)
        stim_params_layout.addLayout(line_box,6,0,1,3)
        stim_params_layout.addWidget(self.null_voltage_label,7,0)
        stim_params_layout.addWidget(self.null_voltage_linedit,7,1)
        stim_params_layout.addLayout(mode_box,8,0)

        # Add image at the bottom of the "Pulse Duration" column
        image_label = QLabel(self)
        pixmap = QPixmap('./laser.png').scaled(128, 128, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        image_label.setPixmap(pixmap)
        image_label.setAlignment(Qt.AlignLeft)
        stim_params_layout.addWidget(image_label, 0, 0, 1, 3)
        stim_params_layout.setAlignment(Qt.AlignLeft)

        main_layout.addWidget(group_box_stim_params, 1, 1)

        # ---------------------- #
        #Phasic stims box
        group_box_phasics = QGroupBox("Phasic stims", self)
        phasics_layout = QGridLayout(group_box_phasics)
        phasics_layout.setAlignment(Qt.AlignTop)

        insp_phasic_button = QPushButton(f"Run inspiratory phasic stims\n({self.insp_phasic_duration:.0f}s of stimulations)", self)
        insp_phasic_button.clicked.connect(self.run_insp_phasic)

        insp_single_pulse = QPushButton(f"Run inspiratory single pulse phasic stims\n({self.insp_phasic_duration:.0f}s of stimulations)", self)
        insp_single_pulse.clicked.connect(self.run_insp_phasic_single_pulse)

        insp_train = QPushButton(f"Run inspiratory train stims\n({self.insp_phasic_duration:.0f}s of stimulations)", self)
        insp_train.clicked.connect(self.run_insp_phasic_train)

        exp_phasic_button = QPushButton(f"Run expiratory phasic stims\n({self.exp_phasic_duration:.0f}s of stimulations)", self)
        exp_phasic_button.clicked.connect(self.run_exp_phasic)
        
        exp_single_pulse = QPushButton(f"Run expiratory single pulse trains\n({self.exp_phasic_duration:.0f}s of stimulations)", self)
        exp_single_pulse.clicked.connect(self.run_exp_phasic_single_pulse)

        exp_train = QPushButton(f"Run expiratory phasic trains\n({self.exp_phasic_duration:.0f}s of stimulations)", self)
        exp_train.clicked.connect(self.run_exp_phasic_train)

        
        tagging_button = QPushButton(f"Run tagging (75 pulses, 3s IPI, 50ms pulse full amp)", self)
        tagging_button.clicked.connect(self.run_tagging)

        phasics_layout.addWidget(insp_phasic_button, 0, 0)
        phasics_layout.addWidget(insp_single_pulse, 1, 0)
        phasics_layout.addWidget(insp_train, 2, 0)
        phasics_layout.addWidget(exp_phasic_button, 0, 1)
        phasics_layout.addWidget(exp_single_pulse, 1, 1)
        phasics_layout.addWidget(exp_train, 2, 1)
        phasics_layout.addWidget(tagging_button, 3, 0)

        main_layout.addWidget(group_box_phasics, 1, 2)

        
        # ---------------------- #
        # Create group box for additional actions (Actions)
        group_box_actions = QGroupBox("Additional Actions", self)
        actions_layout = QGridLayout(group_box_actions)
        actions_layout.setAlignment(Qt.AlignTop)

        # Create action buttons
        start_camera_button = QPushButton("Start Camera (120fps)", self)
        start_camera_button.clicked.connect(self.start_camera_trig)

        stop_camera_button = QPushButton("Stop Camera", self)
        stop_camera_button.clicked.connect(self.stop_camera_trig)

        play_tone_button = QPushButton("Play Tone", self)
        play_tone_button.clicked.connect(self.play_tone)

        play_sync_button = QPushButton("Play Synchronize", self)
        play_sync_button.clicked.connect(self.synch_audio)

        # calibrate_button = QPushButton("Manual calibrate laser", self)
        # calibrate_button.clicked.connect(lambda: self.calibrate_laser())
        # calibrate_button.setStyleSheet("background-color: #801502")

        auto_calibrate_button = QPushButton("AUTO calibrate laser", self)
        auto_calibrate_button.clicked.connect(lambda: self.auto_calibrate_laser())

        max_milliwatt_label = QLabel('Photometer max power: (0-1000mw)')
        self.max_milliwatt_lineedit = QLineEdit()
        self.max_milliwatt_lineedit.setText(f'{self.controller.MAX_MILLIWATTAGE:.0f}')
        self.max_milliwatt_lineedit.setValidator(QDoubleValidator(0.0,1000.0,1))
        self.max_milliwatt_lineedit.textChanged.connect(self.update_max_milliwattage)

        wavelength_selector = QComboBox(self)
        wavelength_selector.addItems(self.implemented_wavelengths)
        wavelength_selector.setCurrentIndex(0)
        wavelength_selector.activated.connect(self.select_wavelength)

        fiber_selector = QComboBox(self)
        fiber_selector.addItems(self.implemented_fibers)
        fiber_selector.setCurrentIndex(0)
        fiber_selector.activated.connect(self.select_fiber)

    
        self.record_button = QPushButton('Start Recording', self)
        self.record_button.setCheckable(True)
        self.record_button.setStyleSheet("background-color: #111111")
        self.record_button.clicked.connect(self.toggle_recording)

        log_label = QLabel('Type your note:')
        self.log_lineedit = QLineEdit()
        self.log_lineedit.setText('')
        self.log_entry_button = QPushButton('Submit note to log')
        self.log_entry_button.clicked.connect(self.submit_log)

        actions_layout.addWidget(start_camera_button, 0, 0)
        actions_layout.addWidget(stop_camera_button, 0, 1)
        actions_layout.addWidget(play_tone_button, 0, 2)
        actions_layout.addWidget(play_sync_button, 0, 3)
        actions_layout.addWidget(wavelength_selector, 2, 0)
        actions_layout.addWidget(fiber_selector,2,1)

        actions_layout.addWidget(max_milliwatt_label,2,2)
        actions_layout.addWidget(self.max_milliwatt_lineedit,2,3)
        actions_layout.addWidget(auto_calibrate_button, 2, 4)


        actions_layout.addWidget(self.record_button, 3, 0)
        actions_layout.addWidget(log_label,4,0)
        actions_layout.addWidget(self.log_lineedit,4,1,1,2)
        actions_layout.addWidget(self.log_entry_button,4,3)

        main_layout.addWidget(group_box_actions, 2, 2)

        # Set up the main window
        self.setLayout(main_layout)
        self.setGeometry(100, 100, 800, 500)
        self.setWindowTitle("Nick's Fancy Experiment Controller (gooey)")
        self.show()
    

    def connect(self):
        if not self.IS_CONNECTED:
            self.controller = nebPod.Controller(self.port)
            self.IS_CONNECTED=True
        else:
            print('Already connected')
    
    def disconnect(self):
        if self.IS_CONNECTED:
            self.controller.serial_port.close()
            self.IS_CONNECTED=False
            print('Disconnected! Warning, GUI will crash if try to use')
        else:
            print('Not connected to any COM port')

    def submit_log(self):
        note = self.log_lineedit.text()
        self.controller.make_log_entry(note,'event')
        self.log_lineedit.setText('')

    def open_valve(self, button_number):
        self.controller.open_valve(button_number,log_style='gas')
        
    def end_hb(self):
        self.controller.end_hb()

    def start_hb(self):
        self.controller.start_hb()

    def timed_hb(self):
        print(f'Running Hering Breuer for {self.hb_time:.2f}s')
        self.controller.timed_hb(self.hb_time)

    def run_pulse(self, duration):
        self.controller.run_pulse(duration,self.laser_amp)
        print(f'Selected pulse duration: {int(1000*duration)}ms, Laser Amplitude: {self.laser_amp:.2f}')

    def run_custom_train(self):
        if 1000/self.train_freq <= self.train_pulse_dur*1000:
            print(f'ERROR: Pulse duration {1000*self.train_pulse_dur} is too long for Frequency {self.train_freq:.2f}')
            self.viz_custom_train()
            return
        print(f'Running custom train\n\tFreq: {self.train_freq:.2f} (Hz)\n\tPulse duration: {1000*self.train_pulse_dur} (ms)\n\tDuration: {self.train_duration} (s)\n\tLaser Amplitude: {self.laser_amp/100:.2f} (V)')
        self.controller.run_train(self.train_duration,
                                  self.train_freq,
                                  self.laser_amp,
                                  self.train_pulse_dur)

    def run_insp_phasic(self):
        print('Running inspiratory phasic stim')
        self.controller.phasic_stim(phase='i',mode='h',n=1,
                                    amp=self.laser_amp,
                                    duration_sec=self.insp_phasic_duration,
                                    intertrain_interval_sec=0.,
                                    )
        
    def run_insp_phasic_train(self):
        print('Running inspiratory phasic train')
        self.controller.phasic_stim(phase='i',mode='t',n=1,
                            amp=self.laser_amp,
                            duration_sec=self.insp_phasic_duration,
                            intertrain_interval_sec=0.,
                            pulse_dur_sec = self.train_pulse_dur,
                            freq = 10
                            )
        
    def run_insp_phasic_single_pulse(self):
        print('running inspiratory phasic single pulse')
        self.controller.phasic_stim(phase='i',mode='p',n=1,
                                    amp=self.laser_amp,
                                    duration_sec=self.insp_phasic_duration,
                                    intertrain_interval_sec=0.,
                                    pulse_dur_sec=self.train_pulse_dur
                                    )
    def run_exp_phasic(self):
        print('Running expiratory phasic stim')
        self.controller.phasic_stim(phase='e',mode='h',n=1,
                            amp=self.laser_amp,
                            duration_sec=self.exp_phasic_duration,
                            intertrain_interval_sec=0.,
                            )

    def run_exp_phasic_train(self):
        print('Running expiratory phasic train')
        self.controller.phasic_stim(phase='e',mode='t',n=1,
                            amp=self.laser_amp,
                            duration_sec=self.exp_phasic_duration,
                            intertrain_interval_sec=0.,
                            pulse_dur_sec = self.train_pulse_dur,
                            freq = 10.0
                            )
        
    def run_exp_phasic_single_pulse(self):
        print('Running expiratory phasic single pulse')
        self.controller.phasic_stim(phase='e',mode='p',n=1,
                                    amp=self.laser_amp,
                                    duration_sec=self.exp_phasic_duration,
                                    intertrain_interval_sec=0.,
                                    pulse_dur_sec=self.train_pulse_dur
                                    )
    def run_tagging(self):
        self.controller.run_tagging()

                
    def play_tone(self):
        self.controller.play_tone(1000,0.5)
        print("Playing a tone")

    def synch_audio(self):
        self.controller.play_synch()
        print("Running audio synch")
        
    def update_hb_time(self,value):
        try:
            self.hb_time = float(value)
        except:
            pass

    def browse_directory(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        directory_path = QFileDialog.getExistingDirectory(self, "Select Directory", "D:/", options=options)
        if directory_path:
            self.file_path_input.setText(directory_path)
            self.save_path = Path(directory_path)
            print(f'Selected save path: {directory_path}')

    def browse_script(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        file_dialog = QFileDialog()
        file_dialog.setOptions(options)
        file_dialog.setDirectory('D:/pyExpControl/python/scripts')
        file_dialog.setFileMode(QFileDialog.AnyFile)
        file_dialog.setNameFilter('*.py')
        if file_dialog.exec_() == QFileDialog.Accepted:
            file_name = file_dialog.selectedFiles()[0]
            self.script_path_input.setText(file_name)
            self.script_filename = Path(file_name)
            print(f'Selected script: {file_name}')

    def run_script(self):
        command = ['python',str(self.script_filename)]
        self.script_run_button.setStyleSheet('background-color: #111111')
        self.setStyleSheet('background-color: #AA1111')
        print('Closing serial port')
        self.controller.serial_port.close()
        self.IS_CONNECTED = False
        QApplication.processEvents()
        subprocess.Popen(' '.join(command))
        QApplication.processEvents()
        # subprocess.run(command)

    def update_train_freq(self,value):
        try:
            self.train_freq = float(value)
        except:
            pass

    def update_train_duration(self,value):
        try:
            self.train_duration = float(value)
        except:
            pass

    def update_train_pulse_dur(self,value):
        try:
            self.train_pulse_dur = float(value)/1000.0
        except:
            pass

    def update_max_milliwattage(self,value):
        try:
            self.controller.set_max_milliwattage(float(value))
        except:
            pass

    def viz_custom_train(self):
        onsets = np.arange(0,self.train_duration*1000,1000/self.train_freq)
        offsets = onsets + 1000*self.train_pulse_dur
        y = np.hstack([np.ones(len(onsets)),np.zeros(len(onsets))])
        t = np.hstack([onsets,offsets])
        idx = np.argsort(t)
        t = t[idx]
        y = y[idx]
        t = np.hstack([[-self.train_duration*1000/2],t,[self.train_duration*1000*3/2]])
        y = np.hstack([[0],y,[0]]) * self.laser_amp

        f = plt.figure(figsize=(8,3))
        plt.step(t,y,'k',where='post')
        plt.xlabel('Time (ms)')
        plt.ylabel('Amplitude (V)')
        plt.gca().spines[['top','right']].set_visible(False)
        if 1000/self.train_freq <= self.train_pulse_dur*1000:
            plt.text(0,0.5,'Frequency/pulse duration mismatch',color='r',size=20,ha='center',va='center')
        plt.ylim(0,1)
        plt.axhline(1,color='k',ls='--')
        plt.axhline(0.5,color='k',ls='--',lw=1)
        plt.yticks([0,0.5,1])

        plt.tight_layout()
        plt.show()
        
    def update_laser_amplitude_from_lineedit(self, value):
        try:
            self.laser_amp = float(value)
        except:
            pass
        self.update_laseramp_dial_value()

    def update_laser_amplitude_from_dial(self, value):
        self.laser_amp = float(value)/100. 
        self.update_laseramp_lineedit_text()
        self.print_laser_amplitude()

    def update_laseramp_dial_value(self):
        self.laser_amp_dial.setValue(int(self.laser_amp*100))

    def update_laseramp_lineedit_text(self):
        self.laser_amp_lineedit.setText(f'{self.laser_amp:.2f}')

    def calibrate_laser(self):
        calib_vals = np.arange(0.5,1.01,0.025)
        on_duration = 5.0
        off_duration = 2.0
        sleep_time = (on_duration+off_duration)
        print("Running Calibration")
        for val in calib_vals:
            self.laser_amp = val
            self.print_laser_amplitude()
            self.run_pulse(on_duration)
            time.sleep(sleep_time)
    
    def auto_calibrate_laser(self):
        volts_supplied,powers = self.controller.auto_calibrate(plot=True)
        data_out = {}
        data_out['command_voltage'] = volts_supplied.tolist()
        data_out['light_power'] = powers.tolist()
        data_out['fiber'] = self.fiber
        data_out['wavelength'] = self.light_wavelength
        save_fn = self.save_path.joinpath('opto_calibration.json')
        print(f'Saving calibration to {save_fn}')
        with open(save_fn,'w') as fid:
            json.dump(data_out, fid,indent=4)


    def select_wavelength(self):
        self.light_wavelength = self.sender().currentText()
        try:
            self.controller.MAX_MILLIWATTAGE = self.powermeter_lims[self.light_wavelength]
        except:
            print('Not changing photometer limits')
        self.max_milliwatt_lineedit.setText(f'{self.controller.MAX_MILLIWATTAGE:.0f}')
        print(f'Selecting {self.light_wavelength} wavelength')

    def select_fiber(self):
        self.fiber = self.sender().currentText()
        print(f'Set fiber to: {self.fiber}')

    def laser_on(self):
        self.controller.turn_on_laser(self.laser_amp)
    
    def laser_off(self):
        self.controller.turn_off_laser(self.laser_amp)

    def print_laser_amplitude(self):
        print(f'Laser amplitude set to: {self.laser_amp:.2f}v')

    def update_null_voltage(self,value):
        try:
            self.null_voltage = float(value)
            self.controller.init_cobalt(mode=self.cobalt_mode,
                                        null_voltage=self.null_voltage)
        except:
            pass
    
    def update_cobalt_mode(self):
        sender = self.sender()
        if sender.isChecked():
            print(f'Selected: {sender.text()} mode')
            self.cobalt_mode = sender.text()[0]
            self.controller.init_cobalt(mode=self.cobalt_mode,
                                        null_voltage=self.null_voltage)
        pass
    
    def start_camera_trig(self):
        self.controller.start_camera_trig(verbose=True)

    def stop_camera_trig(self):
        self.controller.stop_camera_trig(verbose=True)
    
    def toggle_recording(self):
        if self.record_button.isChecked():
            self.record_button.setText('Stop Recording')
            self.start_record()
            self.record_button.setStyleSheet("background-color: #AA1111" )

        else:
            self.record_button.setText('Start recording')
            self.record_button.setStyleSheet("background-color: #111111" )
            self.stop_record()

    def start_record(self):
        self.controller.log = []
        self.controller.start_recording(silent=True)

    def stop_record(self):
        print('stopping recording...')
        self.controller.stop_recording(reset_to_O2=False,silent=True,verbose=False)
        now = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        self.controller.save_log(path = Path(r'D:/'), filename=f'log_{now}.tsv')


    # Shutdown
    def closeEvent(self, event):
        # Close the ArCOM port when the application is closed
        # self.open_valve(0,1) -- Uncomment this to default to O2 on close
        self.controller.serial_port.serialObject.read_all()
        if self.IS_CONNECTED:
            self.controller.serial_port.close()
            self.IS_CONNECTED = False
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    if HAS_STYLING:
        qdarktheme.setup_theme('dark')
    
    window = ArduinoController()
    sys.exit(app.exec_())
