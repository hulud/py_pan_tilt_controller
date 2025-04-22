#!/usr/bin/env python3
import sys
from PyQt5.QtWidgets import QApplication
from gui.main_window import MainWindow
from pelco_D import PelcoDController

def main():
    """Application entry point"""
    # Parse command line arguments
    port = 'COM3'
    baudrate = 9600
    address = 1
    
    if len(sys.argv) > 1:
        port = sys.argv[1]
    if len(sys.argv) > 2:
        try:
            baudrate = int(sys.argv[2])
        except ValueError:
            print(f"Invalid baudrate: {sys.argv[2]}, using default: {baudrate}")
    if len(sys.argv) > 3:
        try:
            address = int(sys.argv[3])
        except ValueError:
            print(f"Invalid address: {sys.argv[3]}, using default: {address}")
    
    # Create Qt application
    app = QApplication(sys.argv)
    
    # Create controller
    try:
        controller = PelcoDController(port=port, baudrate=baudrate, address=address)
    except Exception as e:
        print(f"Error initializing controller: {e}")
        return 1
    
    # Create and show main window
    window = MainWindow(controller)
    window.show()
    
    # Run application
    return app.exec_()

if __name__ == "__main__":
    sys.exit(main())
