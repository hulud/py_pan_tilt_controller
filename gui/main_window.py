#!/usr/bin/env python3
from PyQt5.QtWidgets import QMainWindow, QVBoxLayout, QWidget
from PyQt5.QtCore import QTimer, pyqtSignal
from gui.position_display import PositionDisplay
from gui.control_panel import ControlPanel

class MainWindow(QMainWindow):
    """Main window for the Pan Tilt Camera Control application - NO SAFETY LIMITS"""
    
    # Signal to update position display safely from any thread
    position_updated = pyqtSignal(float, float, float, float)
    
    def __init__(self, controller, parent=None):
        super().__init__(parent)
        
        # Store controller reference
        self.controller = controller
        
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

        # Enable absolute positioning by default (no safety)
        self.controller.abs_positioning_override = True
    
    def init_ui(self):
        """Set up the user interface"""
        self.setWindowTitle('Pan Tilt Camera Control')
        self.setGeometry(100, 100, 600, 500)
        
        # Main layout
        main_layout = QVBoxLayout()
        
        # Position display
        self.position_display = PositionDisplay()
        main_layout.addWidget(self.position_display)
        
        # Control panel
        self.control_panel = ControlPanel(self)
        main_layout.addWidget(self.control_panel)
        
        # Set up main widget
        main_widget = QWidget()
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        
        # Connect control panel signals
        self.control_panel.step_movement_requested.connect(self.handle_step_movement)
        self.control_panel.home_set_requested.connect(self.set_home_position)
    
    def set_home_position(self):
        """Set current position as home position"""
        self.controller.set_home_position()
    
    def update_position(self):
        """Update position display with current values"""
        rel_pan, rel_tilt, raw_pan, raw_tilt = self.controller.get_relative_position()
        if raw_pan is not None and raw_tilt is not None:
            self.position_display.update_display(rel_pan, rel_tilt, raw_pan, raw_tilt)
    
    def on_position_updated(self, rel_pan, rel_tilt, raw_pan, raw_tilt):
        """Handle position updated signal from other threads"""
        self.position_display.update_display(rel_pan, rel_tilt, raw_pan, raw_tilt)
    
    def handle_step_movement(self, direction, step_size):
        """Execute step-based movement in the specified direction"""
        if direction == 'stop':
            self.controller.stop()
            return
            
        # Limit step size to 10 degrees
        if abs(step_size) > 10.0:
            step_size = 10.0 if step_size > 0 else -10.0
            
        # Get current position
        pan, tilt = self.controller.query_position()
        if pan is None or tilt is None:
            return
            
        # Calculate new position based on direction and step size
        if direction == 'up':
            new_tilt = tilt + step_size
            self.controller.absolute_tilt(new_tilt)
        elif direction == 'down':
            new_tilt = tilt - step_size
            self.controller.absolute_tilt(new_tilt)
        elif direction == 'left':
            new_pan = pan - step_size
            if new_pan < 0:
                new_pan += 360
            self.controller.absolute_pan(new_pan)
        elif direction == 'right':
            new_pan = pan + step_size
            if new_pan >= 360:
                new_pan -= 360
            self.controller.absolute_pan(new_pan)
    
    def go_to_absolute_position(self, pan, tilt):
        """Go to the specified absolute position"""
        self.controller.absolute_pan(pan)
        self.controller.absolute_tilt(tilt)
    
    def closeEvent(self, event):
        """Handle window close event"""
        # Stop any movement
        self.controller.stop()
        
        # Stop timers
        self.position_timer.stop()
        
        # Close controller
        self.controller.close()
        event.accept()
