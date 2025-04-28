#!/usr/bin/env python3
"""
simulator_connection.py
=======================
A simulated connection for Pelco D protocol testing.

This module provides a simulated serial connection that can be used
for testing without actual hardware. It simulates a Pelco D compatible
device by implementing the ConnectionBase interface.
"""

import time
import logging
import threading
import queue
from typing import Dict, Any, Optional, Callable

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format="%(asctime)s %(levelname)-8s| %(message)s")
logger = logging.getLogger("simulator_connection")


class SimulatorConnection:
    """
    Simulated connection for testing without physical hardware.
    
    This class implements a simulated serial connection that responds
    to Pelco D protocol commands like a real pan-tilt device.
    """
    
    def __init__(self):
        """Initialize the simulator connection"""
        # Connection state
        self._is_open = False
        
        # Device state
        self.device_state = PelcoDDeviceState()
        
        # Communication buffers
        self._tx_buffer = queue.Queue()  # Commands sent to device
        self._rx_buffer = queue.Queue()  # Responses from device
        
        # Callback for data reception
        self._callback = None
        self._callback_active = False
        self._callback_thread = None
        
        # Processing thread
        self._processing_thread = None
        self._running = False
    
    def open(self) -> bool:
        """
        Open the simulated connection.
        
        Returns:
            True if successfully opened, False otherwise
        """
        if self._is_open:
            return True
            
        try:
            # Clear buffers
            while not self._tx_buffer.empty():
                self._tx_buffer.get_nowait()
            while not self._rx_buffer.empty():
                self._rx_buffer.get_nowait()
            
            # Start processing thread
            self._running = True
            self._processing_thread = threading.Thread(target=self._process_commands)
            self._processing_thread.daemon = True
            self._processing_thread.start()
            
            self._is_open = True
            logger.info("Simulator connection opened")
            return True
        except Exception as e:
            logger.error(f"Error opening simulator connection: {e}")
            self._is_open = False
            return False
    
    def close(self) -> bool:
        """
        Close the simulated connection.
        
        Returns:
            True if successfully closed, False otherwise
        """
        try:
            self._running = False
            
            # Stop callback if active
            if self._callback_active:
                self.unregister_receive_callback()
            
            # Wait for processing thread to finish
            if self._processing_thread:
                self._processing_thread.join(timeout=1.0)
                self._processing_thread = None
            
            # Clear buffers
            while not self._tx_buffer.empty():
                self._tx_buffer.get_nowait()
            while not self._rx_buffer.empty():
                self._rx_buffer.get_nowait()
            
            self._is_open = False
            logger.info("Simulator connection closed")
            return True
        except Exception as e:
            logger.error(f"Error closing simulator connection: {e}")
            return False
    
    def is_open(self) -> bool:
        """
        Check if the connection is open.
        
        Returns:
            True if open, False otherwise
        """
        return self._is_open
    
    def send(self, data: bytes) -> int:
        """
        Send data to the simulated device.
        
        Args:
            data: Command bytes to send
            
        Returns:
            Number of bytes sent
            
        Raises:
            ConnectionError: If the connection is not open
        """
        if not self._is_open:
            raise ConnectionError("Simulator connection is not open")
        
        # Log the sent data
        logger.info(f"TX: {' '.join(f'{b:02X}' for b in data)}")
        
        # Put data in TX buffer
        self._tx_buffer.put(data)
        
        return len(data)
    
    def receive(self, size: int = 1024, timeout: float = 1.0) -> bytes:
        """
        Receive data from the simulated device.
        
        Args:
            size: Maximum number of bytes to receive
            timeout: Maximum time to wait for data in seconds
            
        Returns:
            Received bytes
            
        Raises:
            ConnectionError: If the connection is not open
            TimeoutError: If no data received within timeout
        """
        if not self._is_open:
            raise ConnectionError("Simulator connection is not open")
        
        try:
            # Wait for data with timeout
            start_time = time.time()
            while time.time() - start_time < timeout:
                try:
                    # Check if there's data in the RX buffer
                    data = self._rx_buffer.get(block=True, timeout=0.1)
                    
                    # Log the received data
                    logger.info(f"RX: {' '.join(f'{b:02X}' for b in data)}")
                    
                    return data
                except queue.Empty:
                    # No data yet, continue waiting
                    pass
            
            # Timeout occurred
            raise TimeoutError("No data received within timeout period")
        except TimeoutError:
            # Re-raise timeout errors
            raise
        except Exception as e:
            logger.error(f"Error receiving data: {e}")
            return b''
    
    def receive_until(self, terminator: bytes, max_size: int = 1024, timeout: float = 1.0) -> bytes:
        """
        Receive data until a specific terminator sequence is encountered.
        
        Args:
            terminator: Bytes sequence that marks the end of transmission
            max_size: Maximum number of bytes to receive
            timeout: Maximum time to wait for data in seconds
            
        Returns:
            Received bytes including the terminator
            
        Raises:
            ConnectionError: If the connection is not open
            TimeoutError: If terminator not received within timeout
        """
        # For simulator, this is the same as regular receive since
        # we're always sending complete messages
        return self.receive(size=max_size, timeout=timeout)
    
    def _process_commands(self):
        """Process commands in the TX buffer and generate responses"""
        while self._running:
            try:
                # Check if there's a command to process
                try:
                    command = self._tx_buffer.get(block=True, timeout=0.1)
                except queue.Empty:
                    continue
                
                # Process the command
                if len(command) == 7 and command[0] == 0xFF:
                    # Extract command components
                    address = command[1]
                    cmd1 = command[2]
                    cmd2 = command[3]
                    data1 = command[4]
                    data2 = command[5]
                    
                    # Check if command is for our device
                    if address == self.device_state.address or address == 0:
                        # Handle different command types
                        
                        # Stop command
                        if cmd1 == 0x00 and cmd2 == 0x00 and data1 == 0x00 and data2 == 0x00:
                            logger.info("Command: Stop")
                            # No response needed
                        
                        # Pan position query
                        elif cmd1 == 0x00 and cmd2 == 0x51:
                            logger.info("Command: Query Pan Position")
                            
                            # Generate response (BIT-CCTV format)
                            pan_pos = self.device_state.pan_position_raw
                            msb = (pan_pos >> 8) & 0xFF
                            lsb = pan_pos & 0xFF
                            checksum = (0x59 + msb + lsb) % 256
                            
                            response = bytes([0x00, 0x59, msb, lsb, checksum])
                            
                            # Small delay to simulate processing
                            time.sleep(0.05)
                            
                            # Add response to RX buffer
                            self._rx_buffer.put(response)
                        
                        # Tilt position query
                        elif cmd1 == 0x00 and cmd2 == 0x53:
                            logger.info("Command: Query Tilt Position")
                            
                            # Generate response (BIT-CCTV format)
                            tilt_pos = self.device_state.tilt_position_raw
                            msb = (tilt_pos >> 8) & 0xFF
                            lsb = tilt_pos & 0xFF
                            checksum = (0x5B + msb + lsb) % 256
                            
                            response = bytes([0x00, 0x5B, msb, lsb, checksum])
                            
                            # Small delay to simulate processing
                            time.sleep(0.05)
                            
                            # Add response to RX buffer
                            self._rx_buffer.put(response)
                        
                        # Absolute pan position
                        elif cmd1 == 0x00 and cmd2 == 0x4B:
                            position = (data1 << 8) | data2
                            angle = position / 100.0
                            logger.info(f"Command: Absolute Pan Position {angle:.2f}°")
                            
                            # Set pan angle
                            self.device_state.set_pan_angle(angle)
                        
                        # Absolute tilt position
                        elif cmd1 == 0x00 and cmd2 == 0x4D:
                            position = (data1 << 8) | data2
                            
                            # Compute angle according to protocol
                            if position <= 18000:
                                angle = -position / 100.0
                            else:
                                angle = (36000 - position) / 100.0
                                
                            logger.info(f"Command: Absolute Tilt Position {angle:.2f}°")
                            
                            # Set tilt angle
                            self.device_state.set_tilt_angle(angle)
                        
                        # Pan/tilt movement commands
                        elif cmd1 == 0x00 and cmd2 == 0x02:  # Right
                            logger.info(f"Command: Pan Right (Speed: {data1})")
                            # Handle movement simulation here if needed
                        
                        elif cmd1 == 0x00 and cmd2 == 0x04:  # Left
                            logger.info(f"Command: Pan Left (Speed: {data1})")
                            # Handle movement simulation here if needed
                        
                        elif cmd1 == 0x00 and cmd2 == 0x08:  # Up
                            logger.info(f"Command: Tilt Up (Speed: {data2})")
                            # Handle movement simulation here if needed
                        
                        elif cmd1 == 0x00 and cmd2 == 0x10:  # Down
                            logger.info(f"Command: Tilt Down (Speed: {data2})")
                            # Handle movement simulation here if needed
                        
                        # Zero point commands
                        elif cmd1 == 0x00 and cmd2 == 0x03 and data2 == 0x67:  # Pan zero
                            logger.info("Command: Set Pan Zero Point")
                            self.device_state.set_pan_zero_point()
                        
                        elif cmd1 == 0x00 and cmd2 == 0x03 and data2 == 0x68:  # Tilt zero
                            logger.info("Command: Set Tilt Zero Point")
                            self.device_state.set_tilt_zero_point()
                        
                        # Other commands
                        else:
                            logger.info(f"Unhandled command: {' '.join(f'{b:02X}' for b in command)}")
                    
                else:
                    logger.warning(f"Invalid command format: {' '.join(f'{b:02X}' for b in command)}")
            
            except Exception as e:
                logger.error(f"Error processing command: {e}")
    
    @property
    def config(self) -> Dict[str, Any]:
        """
        Get the current connection configuration.
        
        Returns:
            Dictionary with configuration parameters
        """
        return {
            'type': 'simulator',
            'port': 'SIMULATOR'
        }
    
    def set_config(self, config: Dict[str, Any]) -> bool:
        """
        Update the connection configuration.
        
        Args:
            config: Dictionary with configuration parameters
            
        Returns:
            True if configuration was successfully updated, False otherwise
        """
        # Simulator doesn't need any configuration
        return True
    
    def register_receive_callback(self, callback: Callable[[bytes], None]) -> bool:
        """
        Register a callback function to be called when data is received.
        
        Args:
            callback: Function that takes received bytes as argument
            
        Returns:
            True if callback was successfully registered, False otherwise
        """
        if not self._is_open:
            return False
        
        # Stop existing callback if active
        if self._callback_active:
            self.unregister_receive_callback()
        
        # Set up new callback
        self._callback = callback
        self._callback_active = True
        self._callback_thread = threading.Thread(target=self._callback_loop)
        self._callback_thread.daemon = True
        self._callback_thread.start()
        
        return True
    
    def _callback_loop(self):
        """Background thread for receive callback"""
        while self._callback_active and self._is_open:
            try:
                # Check for data in the RX buffer
                try:
                    data = self._rx_buffer.get(block=True, timeout=0.1)
                    
                    # Call the callback with the data
                    if self._callback:
                        self._callback(data)
                except queue.Empty:
                    # No data yet, continue waiting
                    pass
                
                # Small sleep to prevent CPU hogging
                time.sleep(0.01)
            except Exception as e:
                logger.error(f"Error in callback loop: {e}")
    
    def unregister_receive_callback(self) -> bool:
        """
        Unregister the currently active receive callback.
        
        Returns:
            True if callback was successfully unregistered, False otherwise
        """
        if not self._callback_active:
            return True
        
        self._callback_active = False
        if self._callback_thread:
            self._callback_thread.join(timeout=1.0)
            self._callback_thread = None
        
        self._callback = None
        return True


class PelcoDDeviceState:
    """
    Represents the state of a Pelco D compatible device
    """
    
    def __init__(self, address: int = 1):
        # Device address (camera ID)
        self.address = address
        
        # Position state (in 0.01 degree units)
        self._pan_position = 0  # Raw value (0-36000) = 0-360°
        self._tilt_position = 0  # Raw value (-9000 to +9000) = -90° to +90°
        
        # Zero point calibration (raw values)
        self._pan_zero_point = 0
        self._tilt_zero_point = 0
    
    @property
    def pan_angle(self) -> float:
        """Get pan angle in degrees"""
        return self._pan_position / 100.0
    
    @property
    def tilt_angle(self) -> float:
        """Get tilt angle in degrees"""
        return self._tilt_position / 100.0
    
    @property
    def pan_position_raw(self) -> int:
        """Get raw pan position value for protocol response"""
        return self._pan_position
    
    @property
    def tilt_position_raw(self) -> int:
        """Get raw tilt position value for protocol response"""
        # For negative angles: value = |angle| * 100
        # For positive angles: value = 36000 - angle * 100
        if self._tilt_position < 0:
            return abs(self._tilt_position)
        else:
            return 36000 - self._tilt_position
    
    def set_pan_angle(self, angle: float) -> None:
        """Set pan angle in degrees"""
        self._pan_position = int((angle % 360.0) * 100)
    
    def set_tilt_angle(self, angle: float) -> None:
        """Set tilt angle in degrees (limited to -90 to +90)"""
        angle = max(-90.0, min(90.0, angle))
        self._tilt_position = int(angle * 100)
    
    def set_pan_zero_point(self) -> None:
        """Set current pan position as zero reference"""
        self._pan_zero_point = self._pan_position
        logger.info(f"Set pan zero point at {self.pan_angle:.2f}°")
    
    def set_tilt_zero_point(self) -> None:
        """Set current tilt position as zero reference"""
        self._tilt_zero_point = self._tilt_position
        logger.info(f"Set tilt zero point at {self.tilt_angle:.2f}°")
