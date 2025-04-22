#!/usr/bin/env python3
from PyQt5.QtWidgets import QGroupBox, QHBoxLayout, QLabel
from PyQt5.QtCore import Qt

class PositionDisplay(QGroupBox):
    """Widget to display current pan/tilt position information"""
    
    def __init__(self, parent=None):
        super().__init__("Position", parent)
        self.init_ui()
    
    def init_ui(self):
        layout = QHBoxLayout()
        
        self.pan_display = QLabel("Pan: --°")
        self.tilt_display = QLabel("Tilt: --°")
        self.raw_pan_display = QLabel("Raw Pan: --°")
        self.raw_tilt_display = QLabel("Raw Tilt: --°")
        
        layout.addWidget(self.pan_display)
        layout.addWidget(self.tilt_display)
        layout.addWidget(self.raw_pan_display)
        layout.addWidget(self.raw_tilt_display)
        
        self.setLayout(layout)
    
    def update_display(self, rel_pan, rel_tilt, raw_pan, raw_tilt):
        """Update the position displays with current values"""
        if raw_pan is not None:
            self.raw_pan_display.setText(f"Raw Pan: {raw_pan:.2f}°")
        if raw_tilt is not None:
            self.raw_tilt_display.setText(f"Raw Tilt: {raw_tilt:.2f}°")
        if rel_pan is not None:
            self.pan_display.setText(f"Pan: {rel_pan:.2f}°")
        if rel_tilt is not None:
            self.tilt_display.setText(f"Tilt: {rel_tilt:.2f}°")
