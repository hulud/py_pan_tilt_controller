#!/usr/bin/env python3
import threading
import time
import logging
from PyQt5.QtWidgets import QMainWindow, QVBoxLayout, QWidget, QMessageBox, QLabel, QStatusBar, QPushButton
from PyQt5.QtCore import QTimer, pyqtSignal, Qt
from PyQt5.QtGui import QColor, QFont
from gui.position_display import PositionDisplay
from gui.control_panel import ControlPanel
from gui.api_client import APIClient
from gui.screen_utils import apply_scaled_font, get_screen_info

logger = logging.getLogger(__name__)

class MainWindowAPI(QMainWindow):
    """Main window for the Pan Tilt Camera Control application using API client"""
    
    # Signal to update position display safely from any thread
    position_updated = pyqtSignal(float, float, float, float)
    
    def __init__(self, api_url='http://localhost:5000', parent=None):
        super().__init__(parent)
        
        # Create API client
        self.api_client = APIClient(server_url=api_url)
        
        # Safety parameters
        self.safety_limit_degrees = 45.0
        self.warning_threshold = 0.85  # Show warning at 85% of limit
        
        # Movement state tracking
        self.is_moving = False
        self.current_movement = None  # Track current movement direction
        
        # Initialize UI
        self.init_ui()
        
        # Connect API client signals
        self.api_client.position_updated.connect(self.on_position_updated)
        self.api_client.connection_status_changed.connect(self.on_connection_status_changed)
    
    def init_ui(self):
        """Set up the user interface"""
        self.setWindowTitle('Pan Tilt Camera Control (API Client)')
        
        # Import here to avoid circular imports
        from src.utils import load_config
        
        # Try to load GUI scaling settings from config
        try:
            config = load_config()
            gui_config = config.get('client', {}).get('gui', {})
            width_scale = float(gui_config.get('width_scale', 0.6))  # Default to 60% of screen width
            height_scale = float(gui_config.get('height_scale', 0.7))  # Default to 70% of screen height
            auto_scale = bool(gui_config.get('auto_scale', True))
        except Exception as e:
            # Fall back to defaults if configuration cannot be loaded
            width_scale = 0.6
            height_scale = 0.7
            auto_scale = True
            logger.warning(f"Could not load GUI scaling settings, using defaults: {e}")
        
        # Get screen dimensions and calculate appropriate window size
        from PyQt5.QtWidgets import QDesktopWidget
        desktop = QDesktopWidget()
        screen_rect = desktop.availableGeometry()
        screen_width, screen_height = screen_rect.width(), screen_rect.height()
        
        if auto_scale:
            # Calculate window size based on scaling factors
            window_width = int(screen_width * width_scale)
            window_height = int(screen_height * height_scale)
            
            # Calculate position to center the window
            position_x = int((screen_width - window_width) / 2)
            position_y = int((screen_height - window_height) / 2)
            
            # Set window geometry
            self.setGeometry(position_x, position_y, window_width, window_height)
        else:
            # Use fixed size if auto scaling is disabled
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
        
        # Apply font scaling based on screen resolution
        try:
            # Load the GUI configuration
            from src.utils import load_config
            config = load_config()
            gui_config = config.get('client', {}).get('gui', {})
            
            # Check if font scaling is enabled
            font_scaling = gui_config.get('font_scaling', True)
            base_font_size = gui_config.get('base_font_size', 10)
            
            if font_scaling:
                # Get screen information
                screen_info = get_screen_info()
                
                # Apply scaled fonts
                self.apply_font_scaling(base_font_size)
                logger.info(f"Applied font scaling for screen resolution: {screen_info['width']}x{screen_info['height']}px")
        except Exception as e:
            logger.warning(f"Could not apply font scaling: {e}")
        
        # Set up status bar with connection indicator
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        
        self.connection_indicator = QLabel("◯ Disconnected")
        self.connection_indicator.setStyleSheet("color: red;")
        self.statusBar.addPermanentWidget(self.connection_indicator)
        
        # Connect control panel signals
        self.control_panel.move_requested.connect(self.handle_movement)
        self.control_panel.home_set_requested.connect(self.set_home_position)
    
    def toggle_abs_positioning(self, enable):
        """Enable or disable absolute positioning override"""
        if enable:
            QMessageBox.warning(self, "Safety Warning", 
                "Absolute positioning override is enabled. Use caution as improper tilt values "
                "may damage the camera. Position values are now displayed in raw encoder units.")
    
    def set_home_position(self):
        """Set current position as home position"""
        # Show immediate UI feedback
        self.control_panel.btn_set_home.setStyleSheet("background-color: #AAFFAA;")
        QTimer.singleShot(200, lambda: self.control_panel.btn_set_home.setStyleSheet(""))
        
        # Call the API client's set_home_position method
        if not self.api_client.set_home_position():
            QMessageBox.warning(self, "Error", f"Failed to set home position: {self.api_client.last_error}")
        else:
            self.statusBar.showMessage("Home position set successfully", 3000)
    
    def go_to_absolute_position(self, pan, tilt):
        """Go to an absolute position"""
        # Validate inputs
        if not (0 <= pan <= 360):
            QMessageBox.warning(self, "Invalid Input", "Pan angle must be between 0 and 360 degrees")
            return
            
        if not (-90 <= tilt <= 90):
            QMessageBox.warning(self, "Invalid Input", "Tilt angle must be between -90 and 90 degrees")
            return
            
        # Stop any current movement
        self.stop_movement()
        
        # Send absolute position command
        if not self.api_client.set_absolute_position(pan=pan, tilt=tilt):
            QMessageBox.warning(self, "Error", f"Failed to set absolute position: {self.api_client.last_error}")
        else:
            self.statusBar.showMessage(f"Moving to absolute position: Pan {pan}°, Tilt {tilt}°", 3000)
    
    def apply_button_style(self, direction):
        """Apply a consistent style to the active button"""
        # Clear all button styles first
        for btn in [self.control_panel.btn_up, self.control_panel.btn_down, 
                   self.control_panel.btn_left, self.control_panel.btn_right]:
            btn.setStyleSheet("")
        
        # Apply style to the active button
        if direction == 'up':
            self.control_panel.btn_up.setStyleSheet("background-color: #77AAFF;")
        elif direction == 'down':
            self.control_panel.btn_down.setStyleSheet("background-color: #77AAFF;")
        elif direction == 'left':
            self.control_panel.btn_left.setStyleSheet("background-color: #77AAFF;")
        elif direction == 'right':
            self.control_panel.btn_right.setStyleSheet("background-color: #77AAFF;")
    
    def clear_movement_feedback(self):
        """Clear all movement feedback UI"""
        for btn in [self.control_panel.btn_up, self.control_panel.btn_down, 
                   self.control_panel.btn_left, self.control_panel.btn_right]:
            btn.setStyleSheet("")
        
        self.current_movement = None
    
    def on_position_updated(self, rel_pan, rel_tilt, raw_pan, raw_tilt):
        """Handle position updated signal from API client"""
        self.position_display.update_display(rel_pan, rel_tilt)
        
        # Update safety indicator
        near_limit = False
        if rel_pan is not None and rel_tilt is not None:
            if (abs(rel_pan) > (self.safety_limit_degrees * self.warning_threshold) or 
                abs(rel_tilt) > (self.safety_limit_degrees * self.warning_threshold)):
                near_limit = True
        
        # Check if position_display has set_limit_indicator method
        if hasattr(self.position_display, 'set_limit_indicator'):
            self.position_display.set_limit_indicator(near_limit)
        
        # Check if position is beyond limits and stop movement
        self.check_position_limits(rel_pan, rel_tilt)
    
    def check_position_limits(self, rel_pan, rel_tilt):
        """Check if current position is beyond limits and stop if necessary"""
        if not self.is_moving or rel_pan is None or rel_tilt is None:
            return
            
        if self.current_movement == 'up' and rel_tilt >= self.safety_limit_degrees:
            self.stop_movement()
            self.statusBar.showMessage(f"Stopped: Reached upper tilt limit", 3000)
        elif self.current_movement == 'down' and rel_tilt <= -self.safety_limit_degrees:
            self.stop_movement()
            self.statusBar.showMessage(f"Stopped: Reached lower tilt limit", 3000)
        elif self.current_movement == 'left' and rel_pan <= -self.safety_limit_degrees:
            self.stop_movement()
            self.statusBar.showMessage(f"Stopped: Reached left pan limit", 3000)
        elif self.current_movement == 'right' and rel_pan >= self.safety_limit_degrees:
            self.stop_movement()
            self.statusBar.showMessage(f"Stopped: Reached right pan limit", 3000)
    
    def on_connection_status_changed(self, connected):
        """Handle connection status changes"""
        if connected:
            self.connection_indicator.setText("● Connected")
            self.connection_indicator.setStyleSheet("color: green;")
        else:
            self.connection_indicator.setText("◯ Disconnected")
            self.connection_indicator.setStyleSheet("color: red;")
    
    def check_safety_limits(self, direction, rel_pan, rel_tilt):
        """Check if movement is safe based on relative position"""
        if rel_pan is None or rel_tilt is None:
            # No home position set, consider all movement safe
            return True
        
        if direction == 'up' and rel_tilt > self.safety_limit_degrees:
            return False
        elif direction == 'down' and rel_tilt < -self.safety_limit_degrees:
            return False
        elif direction == 'left' and rel_pan < -self.safety_limit_degrees:
            return False
        elif direction == 'right' and rel_pan > self.safety_limit_degrees:
            return False
        
        return True
    
    def handle_movement(self, direction, speed):
        """Handle continuous movement requests from the control panel"""
        logger.debug(f"Handle movement: direction={direction}, speed={speed}")
        
        if direction == 'stop':
            self.stop_movement()
            return
            
        # Get current position
        position = self.api_client.get_position()
        if not position:
            QMessageBox.warning(self, "Error", f"Failed to get position: {self.api_client.last_error}")
            return
        
        rel_pan, rel_tilt, raw_pan, raw_tilt = position
        
        # Check safety limits locally
        if not self.check_safety_limits(direction, rel_pan, rel_tilt):
            QMessageBox.warning(self, "Safety Limit", 
                f"Cannot move {direction}: would exceed 45° safety limit from home position")
            return
        
        # Start UI feedback immediately
        self.current_movement = direction
        self.apply_button_style(direction)
        
        # Send the move command
        if not self.api_client.move(direction=direction, speed=speed):
            QMessageBox.warning(self, "Error", f"Failed to start {direction} movement: {self.api_client.last_error}")
            self.clear_movement_feedback()
            return
        
        # Mark as moving
        self.is_moving = True
        
        # Show status message
        self.statusBar.showMessage(f"Moving {direction} at speed {speed}", 2000)

    def stop_movement(self):
        """Stop all movement"""
        logger.debug("Stopping all movement")
        self.api_client.move(direction='stop', speed=0)
        self.is_moving = False
        self.clear_movement_feedback()
    
    def apply_font_scaling(self, base_size=10):
        """Apply font scaling to all widgets based on screen resolution"""
        # Apply scaled font to main window
        apply_scaled_font(self, base_size)
        
        # Apply scaled font to position display
        apply_scaled_font(self.position_display, base_size)
        
        # Apply scaled font to control panel and its children
        apply_scaled_font(self.control_panel, base_size)
        
        # Apply scaled font to all buttons in the control panel
        for button in self.control_panel.findChildren(QPushButton):
            apply_scaled_font(button, base_size)
        
        # Apply scaled font to all labels
        for label in self.findChildren(QLabel):
            apply_scaled_font(label, base_size)
        
        # Apply scaled font to status bar
        apply_scaled_font(self.statusBar, base_size - 1)  # Slightly smaller font for status bar
    
    def closeEvent(self, event):
        """Handle window close event"""
        # Stop any movement
        self.stop_movement()
        
        try:
            # Close API client with a timeout to prevent hanging
            threading.Thread(target=self.api_client.close, daemon=True).start()
            time.sleep(0.2)  # Brief delay to allow clean shutdown
        except Exception as e:
            print(f"Error during shutdown: {e}")
            
        event.accept()
