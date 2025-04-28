#!/usr/bin/env python3
"""
simple_demo.py
==============
A simplified demo of the Pelco D simulator using the SimulatorConnection class.

This script:
1. Creates a SimulatorConnection
2. Sends various commands
3. Handles responses
"""

import time
import logging
import argparse
from src.connection.simulator_connection import SimulatorConnection

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format="%(asctime)s %(levelname)-8s| %(message)s")
logger = logging.getLogger("simple_demo")


def calculate_checksum(message):
    """Calculate Pelco D checksum for a list of bytes"""
    # Skip sync byte (first byte) in checksum calculation
    checksum = sum(message[1:]) % 256
    return checksum


def create_command(address, cmd1, cmd2, data1, data2):
    """Create a Pelco D command"""
    message = [0xFF, address, cmd1, cmd2, data1, data2]
    checksum = calculate_checksum(message)
    message.append(checksum)
    return bytes(message)


def run_demo(address=1):
    """Run a simple demo sequence"""
    logger.info("=== Starting Pelco D Simulator Demo ===")
    
    # Create simulator connection
    simulator = SimulatorConnection()
    
    # Open connection
    if not simulator.open():
        logger.error("Failed to open simulator connection")
        return
    
    try:
        # Set initial position
        logger.info("Setting initial position...")
        simulator.device_state.set_pan_angle(180.0)
        simulator.device_state.set_tilt_angle(0.0)
        
        # Query pan position
        logger.info("\n=== Querying Pan Position ===")
        command = create_command(address, 0x00, 0x51, 0x00, 0x00)
        simulator.send(command)
        
        # Receive response
        try:
            response = simulator.receive(timeout=1.0)
            if response and len(response) == 5 and response[1] == 0x59:
                msb = response[2]
                lsb = response[3]
                raw_position = (msb << 8) | lsb
                angle = raw_position / 100.0
                logger.info(f"Pan position: {angle:.2f}°")
            else:
                logger.warning(f"Invalid pan position response: {response.hex() if response else 'None'}")
        except TimeoutError:
            logger.error("Timeout waiting for pan position response")
        
        # Query tilt position
        logger.info("\n=== Querying Tilt Position ===")
        command = create_command(address, 0x00, 0x53, 0x00, 0x00)
        simulator.send(command)
        
        # Receive response
        try:
            response = simulator.receive(timeout=1.0)
            if response and len(response) == 5 and response[1] == 0x5B:
                msb = response[2]
                lsb = response[3]
                raw_position = (msb << 8) | lsb
                
                # Calculate angle according to protocol
                if raw_position > 18000:
                    angle = (36000 - raw_position) / 100.0
                else:
                    angle = -(raw_position / 100.0)
                    
                logger.info(f"Tilt position: {angle:.2f}°")
            else:
                logger.warning(f"Invalid tilt position response: {response.hex() if response else 'None'}")
        except TimeoutError:
            logger.error("Timeout waiting for tilt position response")
        
        # Move to absolute position
        logger.info("\n=== Moving to Absolute Position ===")
        logger.info("Moving to pan=90°, tilt=30°...")
        
        # Pan to 90 degrees
        pan_angle = 90.0
        pan_value = int(pan_angle * 100)
        pan_data1 = (pan_value >> 8) & 0xFF
        pan_data2 = pan_value & 0xFF
        command = create_command(address, 0x00, 0x4B, pan_data1, pan_data2)
        simulator.send(command)
        time.sleep(0.2)
        
        # Tilt to 30 degrees
        tilt_angle = 30.0
        tilt_value = 36000 - int(tilt_angle * 100)  # For positive angles
        tilt_data1 = (tilt_value >> 8) & 0xFF
        tilt_data2 = tilt_value & 0xFF
        command = create_command(address, 0x00, 0x4D, tilt_data1, tilt_data2)
        simulator.send(command)
        time.sleep(0.2)
        
        # Query positions after movement
        logger.info("Querying position after movement...")
        
        # Query pan position
        command = create_command(address, 0x00, 0x51, 0x00, 0x00)
        simulator.send(command)
        try:
            response = simulator.receive(timeout=1.0)
            if response and len(response) == 5 and response[1] == 0x59:
                msb = response[2]
                lsb = response[3]
                raw_position = (msb << 8) | lsb
                angle = raw_position / 100.0
                logger.info(f"Pan position after movement: {angle:.2f}°")
        except TimeoutError:
            logger.error("Timeout waiting for pan position response")
        
        # Query tilt position
        command = create_command(address, 0x00, 0x53, 0x00, 0x00)
        simulator.send(command)
        try:
            response = simulator.receive(timeout=1.0)
            if response and len(response) == 5 and response[1] == 0x5B:
                msb = response[2]
                lsb = response[3]
                raw_position = (msb << 8) | lsb
                if raw_position > 18000:
                    angle = (36000 - raw_position) / 100.0
                else:
                    angle = -(raw_position / 100.0)
                logger.info(f"Tilt position after movement: {angle:.2f}°")
        except TimeoutError:
            logger.error("Timeout waiting for tilt position response")
        
        # Set zero points
        logger.info("\n=== Setting Zero Points ===")
        
        # Set pan zero point
        command = create_command(address, 0x00, 0x03, 0x00, 0x67)
        simulator.send(command)
        time.sleep(0.2)
        
        # Set tilt zero point
        command = create_command(address, 0x00, 0x03, 0x00, 0x68)
        simulator.send(command)
        time.sleep(0.2)
        
        logger.info("Zero points set successfully")
        
    finally:
        # Close simulator
        simulator.close()
        logger.info("Simulator connection closed")
    
    logger.info("=== Demo Complete ===")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Pelco D Simulator Demo")
    parser.add_argument("--addr", type=int, default=1, help="Device address")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    
    args = parser.parse_args()
    
    # Set debug level if requested
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Run the demo
    run_demo(address=args.addr)


if __name__ == "__main__":
    main()
