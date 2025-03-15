from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QProgressBar, 
    QLabel, QScrollArea, QFrame, QApplication, QDialog, QPushButton
)
from PyQt5.QtCore import Qt
from datetime import datetime
import time
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
import json
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QLineEdit, QHBoxLayout
import numpy as np
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton
from PyQt5.QtCore import Qt

AVAILABLE_ODORS = ['H20','Not Connected','octanal','nh3','vanilla','bedding']

def mW_to_volts(mW, power, command_voltage):
    return np.interp(mW, power, command_voltage)


def volts_to_mW(volts, power, command_voltage):
    return np.interp(volts, command_voltage, power)

class StatusWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle('Experiment Status')
        self.setGeometry(100, 100, 600, 400)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Create status label
        self.status_label = QLabel('Ready')
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
        # Create progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Create scroll area for log messages
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        
        # Create log container
        self.log_widget = QWidget()
        self.log_layout = QVBoxLayout(self.log_widget)
        self.log_layout.setAlignment(Qt.AlignTop)
        
        scroll.setWidget(self.log_widget)
        layout.addWidget(scroll)
        
    def update_status(self, message):
        """Update the status label with a message"""
        self.status_label.setText(message)
        self.add_log_message(message)
        QApplication.processEvents()
        
    def set_progress(self, value, maximum=100):
        """Update the progress bar"""
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(maximum)
        self.progress_bar.setValue(value)
        QApplication.processEvents()
        
    def hide_progress(self):
        """Hide the progress bar"""
        self.progress_bar.setVisible(False)
        QApplication.processEvents()
        
    def add_log_message(self, message):
        """Add a message to the log area"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_label = QLabel(f'[{timestamp}] {message}')
        self.log_layout.insertWidget(0, log_label)
        QApplication.processEvents()

class UserDelay(QDialog):
    def __init__(self, prompt):
        super().__init__()
        app = QApplication.instance()
        layout = QVBoxLayout()
        
        label = QLabel(prompt)
        label.setStyleSheet("font-size: 24px;")
        layout.addWidget(label)
        
        continue_button = QPushButton("Continue")
        continue_button.setStyleSheet("font-size: 24px;")
        layout.addWidget(continue_button)
        
        self.setLayout(layout)
        self.setWindowTitle("Waiting for user input")
        self.setGeometry(200, 200, 400, 200)
        self.setStyleSheet("background-color: #f1948a;")
        self.show()
        
        continue_button.clicked.connect(self.close)

class WaitDialog(QDialog):
    def __init__(self, wait_time_sec, msg=None, close_on_finish=True):
        super().__init__()
        self.wait_time_sec = int(wait_time_sec)
        self.msg = msg or "Waiting"
        self.cancelled = False
        self.close_on_finish = close_on_finish
        self.initUI()
        
    def initUI(self):
        layout = QVBoxLayout()
        
        # Message label
        self.label = QLabel(self.msg)
        self.label.setStyleSheet("font-size: 18px;")
        self.label.setAlignment(Qt.AlignLeft)
        layout.addWidget(self.label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        # Skip button
        skip_button = QPushButton("Skip Wait")
        skip_button.setStyleSheet("font-size: 16px;")
        skip_button.clicked.connect(self.cancel_wait)
        layout.addWidget(skip_button)
        
        self.setLayout(layout)
        self.setWindowTitle("Wait Progress")
        self.setGeometry(200, 200, 400, 150)
        
    def cancel_wait(self):
        self.cancelled = True
        if self.close_on_finish:
            self.close()
        
    def wait(self):
        """Execute the wait operation. Returns True if completed, False if cancelled."""
        self.show()
        t_start = time.time()
        
        while time.time() - t_start < self.wait_time_sec:
            if self.cancelled:
                return False
            remaining = self.wait_time_sec - (time.time() - t_start)
            progress = int(((time.time() - t_start) / self.wait_time_sec) * 100)
            self.progress_bar.setValue(progress)
            # Update remaining time in label
            minutes = int(remaining // 60)
            seconds = int(remaining % 60)
            if minutes > 0:
                self.label.setText(f"{self.msg}\nRemaining: {minutes:02d}:{seconds:02d}")
            else:
                self.label.setText(f"{self.msg}\nRemaining: {remaining:0.0f}s")
            
            QApplication.processEvents()
            time.sleep(0.1)
            
        if self.close_on_finish:
            self.close()
        else:
            self.label.setText(f"{self.msg}\nCompleted!")
            self.progress_bar.setValue(100)
            
        return True


class LaserAmpDialog(QDialog):
    def __init__(self, multi=False, calibration_data=None, no_input=False):
        super().__init__()
        self.multi = multi
        self.calibration_data = calibration_data
        self.no_input = no_input
        self.figure = plt.figure()
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.amplitudes = []
        self.amplitude = None
        self.input_mode = (
            "mW" if calibration_data else "volts"
        )  # Default to mW if calibration data is provided
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        self.load_button = QPushButton("Load Calibration File", self)
        self.load_button.clicked.connect(self.load_calibration_file)
        layout.addWidget(self.load_button)

        self.calibration_plot_layout = QVBoxLayout()
        self.calibration_plot_widget = QWidget(self)
        self.calibration_plot_layout.addWidget(self.calibration_plot_widget)
        layout.addLayout(self.calibration_plot_layout)

        self.setWindowTitle("Set Laser Amplitude")
        layout_vals = QHBoxLayout()
        layout.addLayout(layout_vals)

        if not self.no_input:
            self.input_mode_toggle = QPushButton(
                "Switch to Volts Input"
                if self.input_mode == "mW"
                else "Switch to mW Input",
                self,
            )
            self.input_mode_toggle.clicked.connect(self.toggle_input_mode)
            layout.addWidget(self.input_mode_toggle)

            if self.multi:
                self.min_label = QLabel(
                    "Min Amplitude (mW):"
                    if self.input_mode == "mW"
                    else "Min Amplitude (0-1):"
                )
                self.min_input = QLineEdit(self)
                layout_vals.addWidget(self.min_label)
                layout_vals.addWidget(self.min_input)

                self.max_label = QLabel(
                    "Max Amplitude (mW):"
                    if self.input_mode == "mW"
                    else "Max Amplitude (0-1):"
                )
                self.max_input = QLineEdit(self)
                layout_vals.addWidget(self.max_label)
                layout_vals.addWidget(self.max_input)

                self.step_label = QLabel(
                    "Step (mW):" if self.input_mode == "mW" else "Step:"
                )
                self.step_input = QLineEdit(self)
                layout_vals.addWidget(self.step_label)
                layout_vals.addWidget(self.step_input)
            else:
                self.label = QLabel(
                    "Set the laser power (mW):"
                    if self.input_mode == "mW"
                    else "Set the laser power (0-1V):"
                )
                self.input = QLineEdit(self)
                layout_vals.addWidget(self.label)
                layout_vals.addWidget(self.input)

        self.ok_button = QPushButton("Submit (or skip if empty)", self)
        self.ok_button.clicked.connect(self.on_ok)
        layout.addWidget(self.ok_button)

        self.setLayout(layout)
        self.setGeometry(100, 100, 800, 600)
        self.plot_calibration_data()

    def toggle_input_mode(self):
        if self.input_mode == "volts":
            self.input_mode = "mW"
            self.input_mode_toggle.setText("Switch to Volts Input")
            if self.multi:
                self.min_label.setText("Min Amplitude (mW):")
                self.max_label.setText("Max Amplitude (mW):")
                self.step_label.setText("Step (mW):")
            else:
                self.label.setText("Set the laser power (mW):")
        else:
            self.input_mode = "volts"
            self.input_mode_toggle.setText("Switch to mW Input")
            if self.multi:
                self.min_label.setText("Min Amplitude (0-1):")
                self.max_label.setText("Max Amplitude (0-1):")
                self.step_label.setText("Step:")
            else:
                self.label.setText("Set the laser power (0-1V):")

    def on_ok(self):
        msg = ""
        try:
            if self.no_input:
                self.accept()
                return

            if self.multi:
                min_val = float(self.min_input.text())
                max_val = float(self.max_input.text())
                step = float(self.step_input.text())
                if self.input_mode == "volts":
                    if not (0 <= min_val <= 1) or not (0 <= max_val <= 1) or step <= 0:
                        msg = "Please enter valid numbers between 0 and 1 for min and max, and a positive number for step."
                        raise ValueError

                if min_val > max_val:
                    msg = "Min amplitude must be less than max amplitude."
                    raise ValueError

                if step > (max_val - min_val):
                    QMessageBox.warning(
                        self, "Step is larger than range", "Setting step to range."
                    )
                    step = max_val - min_val

                if min_val == max_val:
                    QMessageBox.warning(
                        self, "Min and Max are equal", "Setting only one value"
                    )
                    min_val = max_val

                if step == 0:
                    vals = [min_val]
                else:
                    vals = np.arange(min_val, max_val + step, step)

                if self.input_mode == "mW":
                    self.amplitudes = self.mW_to_volts(vals)
                else:
                    self.amplitudes = vals

                self.accept()
            else:
                val = float(self.input.text())
                if self.input_mode == "volts" and not (0 <= val <= 1):
                    msg = "Please enter a valid number between 0 and 1."
                    raise ValueError
                if self.input_mode == "mW":
                    self.amplitudes = self.mW_to_volts([val])
                else:
                    self.amplitudes = [val]
                self.accept()
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", msg)

    def load_calibration_file(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Load Calibration File", "", "JSON Files (*.json)", options=options
        )
        if file_name:
            with open(file_name, "r") as fid:
                self.calibration_data = json.load(fid)
            self.plot_calibration_data()
            if (not self.no_input) and (self.input_mode == "volts"):
                self.toggle_input_mode()

    def plot_calibration_data(self):
        colors = {"473nm": "#00b7ff", "635nm": "#ff3900", "undefined": "k"}
        self.figure.clear()
        if self.calibration_data is None:
            plt.text(
                0.5,
                0.5,
                "No calibration data loaded",
                ha="center",
                va="center",
                fontsize=16,
            )
            plt.xlim(0, 1)
            plt.ylim(0, 10)
        else:
            volts_supplied = np.array(self.calibration_data["command_voltage"])
            powers = np.array(self.calibration_data["light_power"])
            plt.plot(
                volts_supplied,
                powers,
                "o-",
                color=colors[self.calibration_data["wavelength"]],
            )
            plt.xlim(0.5, np.max(volts_supplied))
            plt.ylim(-1, np.max(powers))

        plt.xlabel("Command Voltage (V)")
        plt.ylabel("Light Power (mW)")
        plt.title("Opto Calibration")
        plt.grid(True)

        # Embed the plot in the QWidget
        self.calibration_plot_layout.addWidget(self.canvas)
        self.canvas.draw()

    def mW_to_volts(self, mW):
        return mW_to_volts(
            mW,
            self.calibration_data["light_power"],
            self.calibration_data["command_voltage"],
        )

    def volts_to_mW(self, volts):
        return volts_to_mW(
            volts,
            self.calibration_data["light_power"],
            self.calibration_data["command_voltage"],
        )

class OdorMapDialog(QDialog):
    def __init__(self, available_odors=None, parent=None):
        super().__init__(parent)
        if available_odors is None:
            available_odors = AVAILABLE_ODORS
        self.available_odors = available_odors
        self.odor_map = {}
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Map Odors left to right (Valve 0 is leftmost)")
        layout = QHBoxLayout(self)

        # Create eight dropdown selectors with labels 0 - 7
        self.combo_boxes = {}
        for i in range(8):
            h_layout = QVBoxLayout()
            label = QLabel(f"Odor {i}:", self)
            combo = QComboBox(self)
            combo.addItems(self.available_odors)
            if i==0:
                combo.setCurrentText('H20')  # Set default odor to 'H20'
            else:
                combo.setCurrentText('Not Connected')  # Set default odor to 'Not Connected'
            self.combo_boxes[i] = combo
            h_layout.addWidget(label)
            h_layout.addWidget(combo)
            layout.addLayout(h_layout)

        # Create Ok and Cancel buttons
        btn_layout = QHBoxLayout()
        ok_button = QPushButton("OK", self)
        ok_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Cancel", self)
        cancel_button.clicked.connect(self.reject)
        btn_layout.addWidget(ok_button)
        btn_layout.addWidget(cancel_button)
        layout.addLayout(btn_layout)

        self.setLayout(layout)
        self.setFixedSize(900, 100)

    def accept(self):
        # Create the mapping from ints 0-7 to the selected odor string
        self.odor_map = {i: self.combo_boxes[i].currentText() for i in range(8)}
        super().accept()