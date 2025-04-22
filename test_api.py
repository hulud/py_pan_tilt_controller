#!/usr/bin/env python3
from pelco_D import PelcoDController

if __name__ == "__main__":
    # Simple test to make sure imports are working correctly
    port = 'COM3'
    baudrate = 9600
    address = 1
    
    try:
        controller = PelcoDController(port=port, baudrate=baudrate, address=address, blocking=True)
        print("Current position:", controller.query_position())
        controller.close()
    except Exception as e:
        print(f"Error: {e}")
