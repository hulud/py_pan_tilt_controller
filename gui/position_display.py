#!/usr/bin/env python3
from PyQt5.QtWidgets import QGroupBox, QHBoxLayout, QLabel, QVBoxLayout
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor

class PositionDisplay(QGroupBox):
    """Widget to display current pan/tilt position information"""
    
    def __init__(self, parent=None):
        super().__init__("Position", parent)
        self.init_ui()
    
    def init_ui(self):
        main_layout = QVBoxLayout()
        position_layout = QHBoxLayout()
        
        self.pan_display = QLabel("Pan: --°")
        self.tilt_display = QLabel("Tilt: --°")
        self.raw_pan_display = QLabel("Raw Pan: --°")
        self.raw_tilt_display = QLabel("Raw Tilt: --°")
        
        position_layout.addWidget(self.pan_display)
        position_layout.addWidget(self.tilt_display)
        position_layout.addWidget(self.raw_pan_display)
        position_layout.addWidget(self.raw_tilt_display)
        
        # Safety limit indicator
        self.limit_indicator = QLabel("■ Within safe range")
        self.limit_indicator.setStyleSheet("color: green; font-weight: bold;")
        
        main_layout.addLayout(position_layout)
        main_layout.addWidget(self.limit_indicator)
        
        self.setLayout(main_layout)
    
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
    
    def set_limit_indicator(self, near_limit):
        """Update the safety limit indicator"""
        if near_limit:
            self.limit_indicator.setText("■ Approaching safety limit")
            self.limit_indicator.setStyleSheet("color: orange; font-weight: bold;")
        else:
            self.limit_indicator.setText("■ Within safe range")
            self.limit_indicator.setStyleSheet("color: green; font-weight: bold;")
