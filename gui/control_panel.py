#!/usr/bin/env python3
from PyQt5.QtWidgets import (QGroupBox, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QDoubleSpinBox)
from PyQt5.QtCore import pyqtSignal, Qt
import logging

logger = logging.getLogger(__name__)

class DirectionButton(QPushButton):
    """Custom button that handles both press and release events for movement control"""
    
    # Signals
    button_pressed = pyqtSignal(str)
    button_released = pyqtSignal(str)
    
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.direction = None
        self.setAutoRepeat(False)  # Disable auto-repeat
    
    def setDirection(self, direction):
        """Set the direction this button controls"""
        self.direction = direction
    
    def mousePressEvent(self, event):
        """Override mousePressEvent to emit button_pressed signal"""
        logger.debug(f"Button {self.direction} pressed")
        super().mousePressEvent(event)
        
        # Emit the button pressed signal with direction
        if self.direction:
            self.button_pressed.emit(self.direction)
    
    def mouseReleaseEvent(self, event):
        """Override mouseReleaseEvent to emit button_released signal"""
        logger.debug(f"Button {self.direction} released")
        super().mouseReleaseEvent(event)
        
        # Emit the button released signal with direction
        if self.direction:
            self.button_released.emit(self.direction)

class ControlPanel(QGroupBox):
    """Widget containing camera movement controls with continuous movement"""
    
    # Signals
    move_requested = pyqtSignal(str, int)  # Direction, speed
    home_set_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__("Controls", parent)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Movement speed parameter
        speed_layout = QHBoxLayout()
        speed_layout.addWidget(QLabel("Speed (1-63):"))
        self.speed_spinbox = QDoubleSpinBox()
        self.speed_spinbox.setRange(1, 63)  # Valid Pelco D speed range
        self.speed_spinbox.setSingleStep(1)
        self.speed_spinbox.setValue(16)  # Default speed (0x10)
        self.speed_spinbox.setDecimals(0)  # Integer values only
        speed_layout.addWidget(self.speed_spinbox)
        
        layout.addLayout(speed_layout)
        
        # Direction controls layout
        direction_layout = QVBoxLayout()
        
        # Top row (UP button)
        top_row = QHBoxLayout()
        top_row.addStretch()
        self.btn_up = DirectionButton("▲")
        self.btn_up.setFixedSize(80, 80)
        self.btn_up.setDirection("up")
        top_row.addWidget(self.btn_up)
        top_row.addStretch()
        direction_layout.addLayout(top_row)
        
        # Middle row (LEFT, STOP, RIGHT buttons)
        middle_row = QHBoxLayout()
        self.btn_left = DirectionButton("◄")
        self.btn_left.setFixedSize(80, 80)
        self.btn_left.setDirection("left")
        self.btn_stop = QPushButton("■")
        self.btn_stop.setFixedSize(80, 80)
        self.btn_right = DirectionButton("►")
        self.btn_right.setFixedSize(80, 80)
        self.btn_right.setDirection("right")
        middle_row.addWidget(self.btn_left)
        middle_row.addWidget(self.btn_stop)
        middle_row.addWidget(self.btn_right)
        direction_layout.addLayout(middle_row)
        
        # Bottom row (DOWN button)
        bottom_row = QHBoxLayout()
        bottom_row.addStretch()
        self.btn_down = DirectionButton("▼")
        self.btn_down.setFixedSize(80, 80)
        self.btn_down.setDirection("down")
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
        
        # Connect movement button events
        self.btn_up.button_pressed.connect(
            lambda: self.handle_direction_pressed('up'))
        self.btn_down.button_pressed.connect(
            lambda: self.handle_direction_pressed('down'))
        self.btn_left.button_pressed.connect(
            lambda: self.handle_direction_pressed('left'))
        self.btn_right.button_pressed.connect(
            lambda: self.handle_direction_pressed('right'))
        
        # Connect button release signals to stop movement
        self.btn_up.button_released.connect(self.on_direction_button_released)
        self.btn_down.button_released.connect(self.on_direction_button_released)
        self.btn_left.button_released.connect(self.on_direction_button_released)
        self.btn_right.button_released.connect(self.on_direction_button_released)
        
        # Connect stop button
        self.btn_stop.clicked.connect(self.handle_stop_clicked)
        
        self.btn_set_home.clicked.connect(self.handle_set_home_clicked)
        
        self.btn_go_abs.clicked.connect(self.go_to_absolute_position)
    
    def handle_direction_pressed(self, direction):
        """Handle direction button press with logging"""
        speed = int(self.speed_spinbox.value())
        logger.debug(f"Direction {direction} pressed with speed {speed}")
        self.move_requested.emit(direction, speed)
    
    def handle_stop_clicked(self):
        """Handle stop button click with logging"""
        logger.debug("Stop button clicked")
        self.move_requested.emit('stop', 0)
    
    def handle_set_home_clicked(self):
        """Handle set home button click with logging"""
        logger.debug("Set home button clicked")
        self.home_set_requested.emit()
        
    def on_direction_button_released(self, direction):
        """Handle direction button release by sending stop command"""
        logger.debug(f"Sending stop command after {direction} button release")
        self.move_requested.emit('stop', 0)
    
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
