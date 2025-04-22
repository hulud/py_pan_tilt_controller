#!/usr/bin/env python3
import threading
import time
from PyQt5.QtWidgets import QMainWindow, QVBoxLayout, QWidget, QMessageBox
from PyQt5.QtCore import QTimer, pyqtSignal
from gui.position_display import PositionDisplay
from gui.control_panel import ControlPanel

class MainWindow(QMainWindow):
    """Main window for the Pan Tilt Camera Control application"""
    
    # Signal to update position display safely from any thread
    position_updated = pyqtSignal(float, float, float, float)
    
    def __init__(self, controller, parent=None):
        super().__init__(parent)
        
        # Store controller reference
        self.controller = controller
        
        # Safety parameters
        self.safety_timer = None
        self.max_continuous_operation = 5.0  # 5 seconds
        self.safety_limit_degrees = self.controller.safety_limit_degrees
        self.warning_threshold = 0.85  # Show warning at 85% of limit
        
        # Movement state tracking
        self.is_moving = False
        
        # Initialize UI
        self.init_ui()
        
        # Create position update timer
        self.position_timer = QTimer()
        self.position_timer.timeout.connect(self.update_position)
        self.position_timer.start(500)  # Update every 500ms
        
        # Connect position update signal
        self.position_updated.connect(self.on_position_updated)
        
        # Initial position update
        self.update_position()
    
    def init_ui(self):
        """Set up the user interface"""
        self.setWindowTitle('Pan Tilt Camera Control')
        self.setGeometry(100, 100, 600, 400)
        
        # Main layout
        main_layout = QVBoxLayout()
        
        # Position display
        self.position_display = PositionDisplay()
        main_layout.addWidget(self.position_display)
        
        # Control panel
        self.control_panel = ControlPanel()
        main_layout.addWidget(self.control_panel)
        
        # Set up main widget
        main_widget = QWidget()
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        
        # Connect control panel signals
        self.control_panel.movement_started.connect(self.start_movement)
        self.control_panel.movement_stopped.connect(self.stop_movement)
        self.control_panel.home_set_requested.connect(self.set_home_position)
        self.control_panel.abs_override_changed.connect(self.toggle_abs_positioning)
    
    def toggle_abs_positioning(self, enable):
        """Enable or disable absolute positioning override"""
        self.controller.set_abs_positioning_override(enable)
        if enable:
            QMessageBox.warning(self, "Safety Warning", 
                "Absolute positioning override is enabled. Use caution as improper tilt values "
                "may damage the camera. Position values are now displayed in raw encoder units.")
    
    def set_home_position(self):
        """Set current position as home position"""
        if self.controller.set_home_position():
            QMessageBox.information(self, "Home Position", 
                "Home position set successfully. Safety limits reset.")
            self.update_position()
        else:
            QMessageBox.warning(self, "Error", "Failed to set home position")
    
    def update_position(self):
        """Update position display with current values"""
        rel_pan, rel_tilt, raw_pan, raw_tilt = self.controller.get_relative_position()
        if raw_pan is not None and raw_tilt is not None:
            self.position_display.update_display(rel_pan, rel_tilt, raw_pan, raw_tilt)
            
            # Update safety indicator
            near_limit = False
            if rel_pan is not None and rel_tilt is not None:
                if (abs(rel_pan) > (self.safety_limit_degrees * self.warning_threshold) or 
                    abs(rel_tilt) > (self.safety_limit_degrees * self.warning_threshold)):
                    near_limit = True
            
            self.control_panel.set_limit_indicator(near_limit)
    
    def on_position_updated(self, rel_pan, rel_tilt, raw_pan, raw_tilt):
        """Handle position updated signal from other threads"""
        self.position_display.update_display(rel_pan, rel_tilt, raw_pan, raw_tilt)
    
    def start_movement(self, direction):
        """Start movement in the specified direction with safety checks"""
        # Check safety limits
        if not self.controller.check_safety_limits(direction):
            QMessageBox.warning(self, "Safety Limit", 
                f"Cannot move {direction}: would exceed 45° safety limit from home position")
            return
        
        # Start the movement
        if direction == 'up':
            self.controller.move_up(speed=0x10)  # Use minimum speed
        elif direction == 'down':
            self.controller.move_down(speed=0x10)  # Use minimum speed
        elif direction == 'left':
            self.controller.move_left(speed=0x10)  # Use minimum speed
        elif direction == 'right':
            self.controller.move_right(speed=0x10)  # Use minimum speed
        
        # Mark as moving
        self.is_moving = True
        
        # Start safety timer
        if self.safety_timer is not None:
            self.safety_timer.cancel()
        
        self.safety_timer = threading.Timer(self.max_continuous_operation, self.safety_stop)
        self.safety_timer.daemon = True
        self.safety_timer.start()
    
    def safety_stop(self):
        """Stop movement due to safety timeout"""
        if self.is_moving:
            self.controller.stop()
            self.is_moving = False
            # Update position
            rel_pan, rel_tilt, raw_pan, raw_tilt = self.controller.get_relative_position()
            if raw_pan is not None and raw_tilt is not None:
                self.position_updated.emit(rel_pan, rel_tilt, raw_pan, raw_tilt)
    
    def stop_movement(self):
        """Stop all movement"""
        self.controller.stop()
        self.is_moving = False
        
        # Cancel safety timer if it's running
        if self.safety_timer is not None:
            self.safety_timer.cancel()
            self.safety_timer = None
    
    def closeEvent(self, event):
        """Handle window close event"""
        # Stop any movement
        self.stop_movement()
        
        # Stop timers
        self.position_timer.stop()
        
        # Close controller
        self.controller.close()
        event.accept()
