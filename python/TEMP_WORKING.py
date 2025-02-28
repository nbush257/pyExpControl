        pwm_gui_box = QGroupBox("PWM settings", self)
        pwm_gui_layout = QGridLayout(pwm_gui_box)
        pwm_gui_layout.setAlignment(Qt.AlignTop)

        # Duty cycle
        train_repFreq_label = QLabel('Train frequency (0-40 Hz)')
        self.train_repFreq_lineedit = QLineEdit()
        self.train_repFreq_lineedit.setText(f'{self.train_repFreq:.0f}')
        self.train_repFreq_lineedit.setValidator(QDoubleValidator(0.0, 40, 0))
        self.train_repFreq_lineedit.textChanged.connect(self.update_train_repFreq)
        
        # Train duration
        train_dur_label = QLabel('Train duration (0s-120s)')
        self.train_dur_lineedit = QLineEdit()
        self.train_dur_lineedit.setText(f'{self.train_duration:.0f}')
        self.train_dur_lineedit.setValidator(QDoubleValidator(0.0, 120.0, 1))
        self.train_dur_lineedit.textChanged.connect(self.update_train_duration)
        # Pulse duration
        train_pulse_dur_label = QLabel('Pulse duration (ms)')
        self.pulse_dur_lineedit = QLineEdit()
        self.pulse_dur_lineedit.setText(f'{1000 * self.train_pulse_dur:.0f}')
        self.pulse_dur_lineedit.setValidator(QIntValidator(0, 1000))
        self.pulse_dur_lineedit.textChanged.connect(self.update_train_pulse_dur)
        # Laser amplitude
        amp_label_text = QLabel('Laser Amp (0-1v):')
        self.laser_amp_lineedit = QLineEdit()
        self.laser_amp_lineedit.setText(f'{self.laser_amp:.2f}')
        self.laser_amp_lineedit.setValidator(QDoubleValidator(0.0, 1.0, 2))
        self.laser_amp_lineedit.textChanged.connect(self.update_laser_amplitude_from_lineedit)
        self.laser_amp_dial = QDial()
        self.laser_amp_dial.setRange(0, 100)
        self.laser_amp_dial.setValue(int(self.laser_amp * 100))
        self.laser_amp_dial.valueChanged.connect(self.update_laser_amplitude_from_dial)

        # Run train button
        train_button = QPushButton('Run custom train', self)
        train_button.clicked.connect(self.run_custom_train)

        # Visualize train button
        viz_train_button = QPushButton('Visualize custom train', self)
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
        self.null_voltage_linedit.setValidator(QDoubleValidator(0.0, 1.0, 2))
        self.null_voltage_linedit.textChanged.connect(self.update_null_voltage)

        # Change digital_laser mode:
        mode_label = QLabel('Select laser mode:')
        self.binary_radio = QRadioButton('Binary')
        self.binary_radio.setChecked(True)
        self.sigmoidal_radio = QRadioButton('Sigmoidal')
        

        # Create a button group to make the radio buttons mutually exclusive
        self.button_group = QButtonGroup()
        self.button_group.addButton(self.binary_radio)
        self.button_group.addButton(self.sigmoidal_radio)
        self.binary_radio.toggled.connect(self.update_digital_laser_mode)
        self.sigmoidal_radio.toggled.connect(self.update_digital_laser_mode)
        mode_box = QHBoxLayout()
        mode_box.addWidget(mode_label)
        mode_box.addWidget(self.binary_radio)
        mode_box.addWidget(self.sigmoidal_radio)