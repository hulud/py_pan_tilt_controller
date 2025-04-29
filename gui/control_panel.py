#!/usr/bin/env python3
from PyQt5.QtWidgets import (QGroupBox, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QDoubleSpinBox)
from PyQt5.QtCore import pyqtSignal

class ControlPanel(QGroupBox):
    """Widget containing camera movement controls with step-based movement"""
    
    # Signals
    step_movement_requested = pyqtSignal(str, float)  # Direction, step size
    home_set_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__("Controls", parent)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Step size parameter
        step_size_layout = QHBoxLayout()
        step_size_layout.addWidget(QLabel("Step Size (degrees):"))
        self.step_size_spinbox = QDoubleSpinBox()
        self.step_size_spinbox.setRange(0.01, 10.0)  # Limit to max 10 degrees, min 0.01
        self.step_size_spinbox.setSingleStep(0.1)
        self.step_size_spinbox.setValue(1.0)
        self.step_size_spinbox.setDecimals(2)  # Allow 0.01 resolution
        step_size_layout.addWidget(self.step_size_spinbox)
        
        layout.addLayout(step_size_layout)
        
        # Direction controls layout
        direction_layout = QVBoxLayout()
        
        # Top row (UP button)
        top_row = QHBoxLayout()
        top_row.addStretch()
        self.btn_up = QPushButton("▲")
        self.btn_up.setFixedSize(80, 80)
        top_row.addWidget(self.btn_up)
        top_row.addStretch()
        direction_layout.addLayout(top_row)
        
        # Middle row (LEFT, STOP, RIGHT buttons)
        middle_row = QHBoxLayout()
        self.btn_left = QPushButton("◄")
        self.btn_left.setFixedSize(80, 80)
        self.btn_stop = QPushButton("■")
        self.btn_stop.setFixedSize(80, 80)
        self.btn_right = QPushButton("►")
        self.btn_right.setFixedSize(80, 80)
        middle_row.addWidget(self.btn_left)
        middle_row.addWidget(self.btn_stop)
        middle_row.addWidget(self.btn_right)
        direction_layout.addLayout(middle_row)
        
        # Bottom row (DOWN button)
        bottom_row = QHBoxLayout()
        bottom_row.addStretch()
        self.btn_down = QPushButton("▼")
        self.btn_down.setFixedSize(80, 80)
        bottom_row.addWidget(self.btn_down)
        bottom_row.addStretch()
        direction_layout.addLayout(bottom_row)
        
        layout.addLayout(direction_layout)
        
        # Home position button
        home_layout = QHBoxLayout()
        self.btn_set_home = QPushButton("Set Current Position as Home")
        home_layout.addWidget(self.btn_set_home)
        layout.addLayout(home_layout)
        
        # Absolute position movement
        abs_pos_layout = QHBoxLayout()
        
        # Pan position input
        pan_layout = QVBoxLayout()
        pan_layout.addWidget(QLabel("Pan Angle:"))
        self.pan_spinbox = QDoubleSpinBox()
        self.pan_spinbox.setRange(-180.0, 180.0)
        self.pan_spinbox.setSingleStep(1.0)
        self.pan_spinbox.setValue(0.0)
        self.pan_spinbox.setDecimals(2)  # Allow 0.01 resolution
        pan_layout.addWidget(self.pan_spinbox)
        
        # Tilt position input
        tilt_layout = QVBoxLayout()
        tilt_layout.addWidget(QLabel("Tilt Angle:"))
        self.tilt_spinbox = QDoubleSpinBox()
        self.tilt_spinbox.setRange(-90.0, 90.0)
        self.tilt_spinbox.setSingleStep(1.0)
        self.tilt_spinbox.setValue(0.0)
        self.tilt_spinbox.setDecimals(2)  # Allow 0.01 resolution
        tilt_layout.addWidget(self.tilt_spinbox)
        
        abs_pos_layout.addLayout(pan_layout)
        abs_pos_layout.addLayout(tilt_layout)
        
        layout.addLayout(abs_pos_layout)
        
        # Go to absolute position button
        go_abs_layout = QHBoxLayout()
        self.btn_go_abs = QPushButton("Go to Absolute Position")
        go_abs_layout.addWidget(self.btn_go_abs)
        layout.addLayout(go_abs_layout)
        
        self.setLayout(layout)
        
        # Connect signals
        self.btn_up.clicked.connect(
            lambda: self.step_movement_requested.emit('up', self.step_size_spinbox.value()))
        
        self.btn_down.clicked.connect(
            lambda: self.step_movement_requested.emit('down', self.step_size_spinbox.value()))
        
        self.btn_left.clicked.connect(
            lambda: self.step_movement_requested.emit('left', self.step_size_spinbox.value()))
        
        self.btn_right.clicked.connect(
            lambda: self.step_movement_requested.emit('right', self.step_size_spinbox.value()))
        
        self.btn_stop.clicked.connect(
            lambda: self.step_movement_requested.emit('stop', 0))
        
        self.btn_set_home.clicked.connect(self.home_set_requested.emit)
        
        self.btn_go_abs.clicked.connect(self.go_to_absolute_position)
    
    def go_to_absolute_position(self):
        """Command the controller to go to the specified absolute position"""
        pan = self.pan_spinbox.value()
        tilt = self.tilt_spinbox.value()
        
        # Get the main window which should be MainWindowAPI
        main_window = self.window()
        if hasattr(main_window, 'go_to_absolute_position'):
            main_window.go_to_absolute_position(pan, tilt)
        else:
            print("Error: Main window doesn't have go_to_absolute_position method")
