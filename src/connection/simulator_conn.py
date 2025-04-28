"""
Simulator connection for PTZ camera testing.

This module provides a simulated connection that mimics the behavior of
a real PTZ camera without requiring actual hardware.
"""
import time
import threading
import logging
from typing import Optional, Dict, Any, Union, Callable, Tuple
from .base import ConnectionBase

logger = logging.getLogger(__name__)

class SimulatorConnection(ConnectionBase):
    """
    Simulated connection for PTZ camera testing.
    
    This class simulates a PTZ camera with Pelco D protocol support
    for development and testing without real hardware.
    """
    
    def __init__(self, 
                port: str = 'SIMULATOR', 
                baudrate: int = 9600,
                **kwargs):
        """
        Initialize simulator connection.
        
        Args:
            port: Should be 'SIMULATOR'
            baudrate: Simulated baud rate (ignored)
            **kwargs: Additional parameters (ignored)
        """
        self._open = False
        self._pan_position = 0.0  # in degrees
        self._tilt_position = 0.0  # in degrees
        self._last_command = None
        self._callback = None
        self._callback_active = False
        self._callback_thread = None
    
    def open(self) -> bool:
        """
        Open the simulated connection.
        
        Returns:
            True always (simulation never fails to open)
        """
        logger.info("Opening simulator connection")
        self._open = True
        return True
    
    def close(self) -> bool:
        """
        Close the simulated connection.
        
        Returns:
            True always
        """
        logger.info("Closing simulator connection")
        
        # Stop callback thread if active
        if self._callback_active:
            self.unregister_receive_callback()
            
        self._open = False
        return True
    
    def is_open(self) -> bool:
        """
        Check if the connection is open.
        
        Returns:
            True if connection is open, False otherwise
        """
        return self._open
    
    def send(self, data: bytes) -> int:
        """
        Send data to the simulated camera.
        
        Args:
            data: Command bytes
            
        Returns:
            Number of bytes sent
            
        Raises:
            ConnectionError: If connection is not open
        """
        if not self.is_open():
            raise ConnectionError("Simulator connection is not open")
        
        # Log the command
        logger.info(f"[SIM TX] >>> {' '.join(f'{b:02X}' for b in data)} | Length: {len(data)} bytes")
        
        # Store the command for later reference
        self._last_command = data
        
        # Process the command
        self._process_command(data)
        
        return len(data)
    
    def receive(self, size: int = 1024, timeout: float = None) -> bytes:
        """
        Receive data from the simulated camera.
        
        If the last command was a query, returns a simulated response.
        
        Args:
            size: Maximum number of bytes to read (ignored)
            timeout: Read timeout in seconds (ignored)
            
        Returns:
            Simulated response bytes
            
        Raises:
            ConnectionError: If connection is not open
        """
        if not self.is_open():
            raise ConnectionError("Simulator connection is not open")
        
        # If no command was sent, return empty
        if not self._last_command:
            return bytes()
        
        # Generate response based on last command
        response = self._generate_response()
        
        # Clear last command to prevent repeated responses
        self._last_command = None
        
        # Log the response
        if response:
            logger.info(f"[SIM RX] <<< {' '.join(f'{b:02X}' for b in response)} | Length: {len(response)} bytes")
        
        # Simulate delay
        time.sleep(0.05)
        
        return response
    
    def receive_until(self, 
                     terminator: bytes, 
                     max_size: int = 1024, 
                     timeout: float = None) -> bytes:
        """
        Receive data until a specific terminator sequence is encountered.
        
        Args:
            terminator: Bytes sequence that marks the end of transmission
            max_size: Maximum number of bytes to receive
            timeout: Maximum time to wait for data in seconds
            
        Returns:
            Received bytes including the terminator
            
        Raises:
            ConnectionError: If connection is not open
        """
        # Just call receive() as our simulator doesn't need to handle terminators
        response = self.receive(max_size, timeout)
        
        # Append terminator if response is not empty
        if response:
            response += terminator
            
        return response
    
    def _process_command(self, data: bytes) -> None:
        """
        Process a command and update the simulator state.
        
        Args:
            data: Command bytes
        """
        # Verify it's a valid Pelco D command
        if len(data) < 7 or data[0] != 0xFF:
            return
            
        # Extract command parts
        address = data[1]
        cmd1 = data[2]
        cmd2 = data[3]
        data1 = data[4]
        data2 = data[5]
        
        # Process different command types
        if cmd1 == 0x00:
            # Stop command
            if cmd2 == 0x00 and data1 == 0x00 and data2 == 0x00:
                logger.info("[SIM] Stop command received")
                
            # Pan right
            elif cmd2 == 0x02:
                speed = data1 / 0x3F  # Normalize speed to 0-1
                angle = speed * 5.0  # Move 0-5 degrees based on speed
                self._pan_position = (self._pan_position + angle) % 360
                logger.info(f"[SIM] Pan right: {angle:.2f}° -> {self._pan_position:.2f}°")
                
            # Pan left
            elif cmd2 == 0x04:
                speed = data1 / 0x3F  # Normalize speed to 0-1
                angle = speed * 5.0  # Move 0-5 degrees based on speed
                self._pan_position = (self._pan_position - angle) % 360
                logger.info(f"[SIM] Pan left: {angle:.2f}° -> {self._pan_position:.2f}°")
                
            # Tilt up
            elif cmd2 == 0x08:
                speed = data2 / 0x3F  # Normalize speed to 0-1
                angle = speed * 3.0  # Move 0-3 degrees based on speed
                self._tilt_position = min(90, self._tilt_position + angle)
                logger.info(f"[SIM] Tilt up: {angle:.2f}° -> {self._tilt_position:.2f}°")
                
            # Tilt down
            elif cmd2 == 0x10:
                speed = data2 / 0x3F  # Normalize speed to 0-1
                angle = speed * 3.0  # Move 0-3 degrees based on speed
                self._tilt_position = max(-90, self._tilt_position - angle)
                logger.info(f"[SIM] Tilt down: {angle:.2f}° -> {self._tilt_position:.2f}°")
                
            # Pan and tilt combinations
            elif cmd2 in [0x0C, 0x14, 0x0A, 0x12]:
                pan_speed = data1 / 0x3F
                tilt_speed = data2 / 0x3F
                pan_angle = pan_speed * 5.0
                tilt_angle = tilt_speed * 3.0
                
                # Left-up
                if cmd2 == 0x0C:
                    self._pan_position = (self._pan_position - pan_angle) % 360
                    self._tilt_position = min(90, self._tilt_position + tilt_angle)
                    logger.info(f"[SIM] Pan left + Tilt up -> {self._pan_position:.2f}°, {self._tilt_position:.2f}°")
                
                # Left-down
                elif cmd2 == 0x14:
                    self._pan_position = (self._pan_position - pan_angle) % 360
                    self._tilt_position = max(-90, self._tilt_position - tilt_angle)
                    logger.info(f"[SIM] Pan left + Tilt down -> {self._pan_position:.2f}°, {self._tilt_position:.2f}°")
                
                # Right-up
                elif cmd2 == 0x0A:
                    self._pan_position = (self._pan_position + pan_angle) % 360
                    self._tilt_position = min(90, self._tilt_position + tilt_angle)
                    logger.info(f"[SIM] Pan right + Tilt up -> {self._pan_position:.2f}°, {self._tilt_position:.2f}°")
                
                # Right-down
                elif cmd2 == 0x12:
                    self._pan_position = (self._pan_position + pan_angle) % 360
                    self._tilt_position = max(-90, self._tilt_position - tilt_angle)
                    logger.info(f"[SIM] Pan right + Tilt down -> {self._pan_position:.2f}°, {self._tilt_position:.2f}°")
            
            # Preset commands
            elif cmd2 == 0x03 and data1 == 0x00:
                if data2 == 0x67:
                    logger.info("[SIM] Set pan zero point")
                    # Zero point doesn't change actual position
                elif data2 == 0x68:
                    logger.info("[SIM] Set tilt zero point")
                    # Zero point doesn't change actual position
                else:
                    logger.info(f"[SIM] Set preset {data2}")
            
            elif cmd2 == 0x07 and data1 == 0x00:
                logger.info(f"[SIM] Call preset {data2}")
                # Move to a simulated preset position
                if data2 == 1:
                    self._pan_position = 0.0
                    self._tilt_position = 0.0
                elif data2 == 2:
                    self._pan_position = 90.0
                    self._tilt_position = 45.0
                elif data2 == 3:
                    self._pan_position = 180.0
                    self._tilt_position = 0.0
                elif data2 == 4:
                    self._pan_position = 270.0
                    self._tilt_position = -45.0
            
            # Position query commands (handled in _generate_response)
            elif cmd2 == 0x51 or cmd2 == 0x53:
                if cmd2 == 0x51:
                    logger.info(f"[SIM] Pan position query -> {self._pan_position:.2f}°")
                else:
                    logger.info(f"[SIM] Tilt position query -> {self._tilt_position:.2f}°")
            
            # Absolute position commands
            elif cmd2 == 0x4B:
                value = (data1 << 8) | data2
                angle = value / 100.0
                self._pan_position = angle % 360.0
                logger.info(f"[SIM] Absolute pan to {angle:.2f}° -> {self._pan_position:.2f}°")
            
            elif cmd2 == 0x4D:
                value = (data1 << 8) | data2
                if value > 18000:
                    angle = (36000 - value) / 100.0
                else:
                    angle = -value / 100.0
                self._tilt_position = max(-90, min(90, angle))
                logger.info(f"[SIM] Absolute tilt to {angle:.2f}° -> {self._tilt_position:.2f}°")
    
    def _generate_response(self) -> bytes:
        """
        Generate a simulated response based on the last command.
        
        Returns:
            Simulated response bytes or empty bytes if no response
        """
        if not self._last_command or len(self._last_command) < 7:
            return bytes()
        
        cmd1 = self._last_command[2]
        cmd2 = self._last_command[3]
        
        # Pan position query
        if cmd1 == 0x00 and cmd2 == 0x51:
            # Convert position to raw value
            pan_value = int(self._pan_position * 100)
            pan_msb = (pan_value >> 8) & 0xFF
            pan_lsb = pan_value & 0xFF
            
            # Use BIT-CCTV custom format (5 bytes, raw response)
            # Format: XX 59 PMSB PLSB SUM
            # Where XX is a random byte that doesn't affect parsing
            response = bytearray([0x00, 0x59, pan_msb, pan_lsb, 0x00])
            # Calculate checksum (sum of first 4 bytes)
            response[4] = sum(response[:4]) % 256
            
            return bytes(response)
        
        # Tilt position query
        elif cmd1 == 0x00 and cmd2 == 0x53:
            # Convert position to raw value per Pelco D spec
            if self._tilt_position >= 0:
                tilt_value = 36000 - int(self._tilt_position * 100)
            else:
                tilt_value = int(abs(self._tilt_position) * 100)
                
            tilt_msb = (tilt_value >> 8) & 0xFF
            tilt_lsb = tilt_value & 0xFF
            
            # Use BIT-CCTV custom format (5 bytes, raw response)
            # Format: XX 5B TMSB TLSB SUM
            # Where XX is a random byte that doesn't affect parsing
            response = bytearray([0x00, 0x5B, tilt_msb, tilt_lsb, 0x00])
            # Calculate checksum (sum of first 4 bytes)
            response[4] = sum(response[:4]) % 256
            
            return bytes(response)
        
        # No response for other commands
        return bytes()
    
    @property
    def config(self) -> Dict[str, Any]:
        """
        Get the current simulator configuration.
        
        Returns:
            Dictionary with configuration parameters
        """
        return {
            'port': 'SIMULATOR',
            'baudrate': 9600
        }
    
    def set_config(self, config: Dict[str, Any]) -> bool:
        """
        Update the simulator configuration (ignored).
        
        Args:
            config: Dictionary with configuration parameters
            
        Returns:
            True always
        """
        # Simulator doesn't need real configuration
        return True
    
    def _callback_loop(self):
        """Background thread for simulated events"""
        while self._callback_active and self._open:
            # No automatic events in this simulator
            time.sleep(0.1)
    
    def register_receive_callback(self, callback: Callable[[bytes], None]) -> bool:
        """
        Register a callback function to be called when data is received.
        
        Args:
            callback: Function that takes received bytes as argument
            
        Returns:
            True if callback was successfully registered, False otherwise
        """
        if not self.is_open():
            return False
        
        # Stop existing callback if active
        if self._callback_active:
            self.unregister_receive_callback()
        
        # Set up new callback
        self._callback = callback
        self._callback_active = True
        self._callback_thread = threading.Thread(target=self._callback_loop, daemon=True)
        self._callback_thread.start()
        
        return True
    
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
