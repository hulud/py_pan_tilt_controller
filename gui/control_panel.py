#!/usr/bin/env python3
from PyQt5.QtWidgets import (QGroupBox, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QCheckBox, QDoubleSpinBox)
from PyQt5.QtCore import Qt, pyqtSignal
from gui.safety_indicator import SafetyLimitIndicator

class ControlPanel(QGroupBox):
    """Widget containing camera movement controls and safety features"""
    
    # Signals
    movement_started = pyqtSignal(str, float, float)  # Direction, time, step size
    movement_stopped = pyqtSignal()
    home_set_requested = pyqtSignal()
    abs_override_changed = pyqtSignal(bool)
    
    def __init__(self, parent=None):
        super().__init__("Controls", parent)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Movement parameters layout
        movement_params_layout = QHBoxLayout()
        
        # Movement time parameter
        movement_time_layout = QVBoxLayout()
        movement_time_layout.addWidget(QLabel("Movement Time (sec):"))
        self.movement_time_spinbox = QDoubleSpinBox()
        self.movement_time_spinbox.setRange(0.1, 10.0)
        self.movement_time_spinbox.setSingleStep(0.1)
        self.movement_time_spinbox.setValue(1.0)
        self.movement_time_spinbox.setDecimals(1)
        movement_time_layout.addWidget(self.movement_time_spinbox)
        movement_params_layout.addLayout(movement_time_layout)
        
        # Step size parameter
        step_size_layout = QVBoxLayout()
        step_size_layout.addWidget(QLabel("Step Size (degrees):"))
        self.step_size_spinbox = QDoubleSpinBox()
        self.step_size_spinbox.setRange(0.1, 45.0)
        self.step_size_spinbox.setSingleStep(0.5)
        self.step_size_spinbox.setValue(5.0)
        self.step_size_spinbox.setDecimals(1)
        step_size_layout.addWidget(self.step_size_spinbox)
        movement_params_layout.addLayout(step_size_layout)
        
        layout.addLayout(movement_params_layout)
        
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
        
        # Safety limit indicator
        limit_layout = QHBoxLayout()
        self.limit_indicator = SafetyLimitIndicator()
        limit_layout.addWidget(QLabel("Safety Limit:"))
        limit_layout.addWidget(self.limit_indicator)
        limit_layout.addStretch()
        layout.addLayout(limit_layout)
        
        # Absolute positioning override
        self.abs_override_check = QCheckBox("Enable Absolute Positioning (Override Safety)")
        layout.addWidget(self.abs_override_check)
        
        self.setLayout(layout)
        
        # Connect signals
        self.btn_up.clicked.connect(
            lambda: self.movement_started.emit('up', self.movement_time_spinbox.value(), self.step_size_spinbox.value()))
        
        self.btn_down.clicked.connect(
            lambda: self.movement_started.emit('down', self.movement_time_spinbox.value(), self.step_size_spinbox.value()))
        
        self.btn_left.clicked.connect(
            lambda: self.movement_started.emit('left', self.movement_time_spinbox.value(), self.step_size_spinbox.value()))
        
        self.btn_right.clicked.connect(
            lambda: self.movement_started.emit('right', self.movement_time_spinbox.value(), self.step_size_spinbox.value()))
        
        self.btn_stop.clicked.connect(self.movement_stopped.emit)
        self.btn_set_home.clicked.connect(self.home_set_requested.emit)
        
        self.abs_override_check.stateChanged.connect(
            lambda state: self.abs_override_changed.emit(state == Qt.Checked))
    
    def set_limit_indicator(self, is_near_limit):
        """Update the safety limit indicator"""
        self.limit_indicator.set_near_limit(is_near_limit)
