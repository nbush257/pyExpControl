from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QProgressBar, 
    QLabel, QScrollArea, QFrame, QApplication, QDialog, QPushButton
)
from PyQt5.QtCore import Qt
from datetime import datetime
import time

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
    def __init__(self, wait_time_sec, msg=None):
        super().__init__()
        self.wait_time_sec = int(wait_time_sec)
        self.msg = msg or "Waiting"
        self.cancelled = False
        self.initUI()
        
    def initUI(self):
        layout = QVBoxLayout()
        
        # Message label
        self.label = QLabel(self.msg)
        self.label.setStyleSheet("font-size: 18px;")
        self.label.setAlignment(Qt.AlignCenter)
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
            # Format remaining time as mm:ss if greater than 1 minute
            minutes = int(remaining // 60)
            seconds = int(remaining % 60)
            if minutes > 0:
                self.label.setText(f"{self.msg}\nRemaining: {minutes:02d}:{seconds:02d}")
            else:
                self.label.setText(f"{self.msg}\nRemaining: {remaining:0.0f}s")
            
            QApplication.processEvents()
            time.sleep(0.1)
            
        self.close()
        return True

