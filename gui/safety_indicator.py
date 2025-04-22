#!/usr/bin/env python3
from PyQt5.QtWidgets import QFrame
from PyQt5.QtGui import QColor, QPalette

class SafetyLimitIndicator(QFrame):
    """Custom widget to show limit warning as a colored indicator"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(20, 20)
        self.setFrameShape(QFrame.Box)
        self.is_near_limit = False
        self.update_color()
    
    def set_near_limit(self, is_near_limit):
        self.is_near_limit = is_near_limit
        self.update_color()
    
    def update_color(self):
        palette = self.palette()
        if self.is_near_limit:
            palette.setColor(QPalette.Background, QColor(255, 0, 0))  # Red
        else:
            palette.setColor(QPalette.Background, QColor(0, 255, 0))  # Green
        self.setAutoFillBackground(True)
        self.setPalette(palette)
