"""
Pan-Tilt-Zoom controller implementation.

This module provides the main controller class for PTZ cameras,
bringing together the protocol and connection modules.
"""
import time
import threading
import logging
from typing import Dict, Any, Optional, Tuple, Callable, List, Union

from ..protocol import PelcoDProtocol
from ..connection import ConnectionBase, SerialConnection, NetworkConnection

logger = logging.getLogger(__name__)


class PTZController:
    """
    PTZ Camera Controller
    
    This class provides a high-level interface for controlling PTZ cameras,
    integrating the protocol and connection modules.
    """
    
    def __init__(self, connection_config: Dict[str, Any], address: int = 1):
        """
        Initialize the PTZ controller.
        
        Args:
            connection_config: Connection configuration
            address: Camera address (1-255)
        """
        self.connection_type = connection_config.get('type', 'serial')
        self.connection = self._create_connection(connection_config)
        self.protocol = PelcoDProtocol(address=address)
        
        # Position tracking
        self.home_pan = None
        self.home_tilt = None
        
        # Initialize connection
        if not self.connection.open():
            raise ConnectionError(f"Failed to open {self.connection_type} connection")
        
        # Wait for device to initialize
        time.sleep(0.5)
        
        # Initialize zero points
        self._init_zero_points()
    
    def _create_connection(self, config: Dict[str, Any]) -> ConnectionBase:
        """
        Create appropriate connection based on config.
        
        Args:
            config: Connection configuration
            
        Returns:
            Connection instance
            
        Raises:
            ValueError: If connection type is invalid
        """
        connection_type = config.get('type', 'serial')
        
        if connection_type == 'serial':
            serial_config = config.get('serial', {})
            return SerialConnection(
                port=serial_config.get('port', 'COM3'),
                baudrate=serial_config.get('baudrate', 9600),
                data_bits=serial_config.get('data_bits', 8),
                stop_bits=serial_config.get('stop_bits', 1),
                parity=serial_config.get('parity', 'N'),
                timeout=serial_config.get('timeout', 1.0)
            )
        elif connection_type == 'network':
            network_config = config.get('network', {})
            return NetworkConnection(
                ip=network_config.get('ip', '192.168.1.60'),
                port=network_config.get('port', 80),
                timeout=network_config.get('timeout', 1.0)
            )
        else:
            raise ValueError(f"Unsupported connection type: {connection_type}")
    
    def _init_zero_points(self):
        """Initialize zero points for pan and tilt axes"""
        logger.info("Setting zero points for pan and tilt axes...")
        self._send_command(self.protocol.set_pan_zero_point())
        time.sleep(0.5)
        self._send_command(self.protocol.set_tilt_zero_point())
        time.sleep(0.5)
        logger.info("Zero points initialized")
    
    def _send_command(self, command: bytes) -> bool:
        """
        Send a command to the device.
        
        Args:
            command: Command bytes to send
            
        Returns:
            True if command was sent successfully, False otherwise
        """
        try:
            self.connection.send(command)
            logger.debug(f"Sent: {' '.join(f'{b:02X}' for b in command)}")
            return True
        except Exception as e:
            logger.error(f"Error sending command: {e}")
            return False
    
    def _read_response(self, expected_length: int = 7, timeout: float = 1.0) -> Optional[bytes]:
        """
        Read response from the device.
        
        Args:
            expected_length: Expected length of response
            timeout: Maximum time to wait for response
            
        Returns:
            Response bytes or None if no response received
        """
        try:
            data = self.connection.receive(size=expected_length, timeout=timeout)
            logger.debug(f"Received: {' '.join(f'{b:02X}' for b in data)}")
            return data
        except Exception as e:
            logger.error(f"Error reading response: {e}")
            return None
    
    # Movement methods
    
    def stop(self) -> bool:
        """
        Stop all movement.
        
        Returns:
            True if command was sent successfully, False otherwise
        """
        logger.info("Stopping movement")
        return self._send_command(self.protocol.stop())
    
    def move_up(self, speed: int = 0x20) -> bool:
        """
        Move up at specified speed.
        
        Args:
            speed: Movement speed (0x00-0x3F)
            
        Returns:
            True if command was sent successfully, False otherwise
        """
        logger.info(f"Moving up at speed {speed:02X}")
        return self._send_command(self.protocol.move_up(speed))
    
    def move_down(self, speed: int = 0x20) -> bool:
        """
        Move down at specified speed.
        
        Args:
            speed: Movement speed (0x00-0x3F)
            
        Returns:
            True if command was sent successfully, False otherwise
        """
        logger.info(f"Moving down at speed {speed:02X}")
        return self._send_command(self.protocol.move_down(speed))
    
    def move_left(self, speed: int = 0x20) -> bool:
        """
        Move left at specified speed.
        
        Args:
            speed: Movement speed (0x00-0x3F)
            
        Returns:
            True if command was sent successfully, False otherwise
        """
        logger.info(f"Moving left at speed {speed:02X}")
        return self._send_command(self.protocol.move_left(speed))
    
    def move_right(self, speed: int = 0x20) -> bool:
        """
        Move right at specified speed.
        
        Args:
            speed: Movement speed (0x00-0x3F)
            
        Returns:
            True if command was sent successfully, False otherwise
        """
        logger.info(f"Moving right at speed {speed:02X}")
        return self._send_command(self.protocol.move_right(speed))
    
    # Position query methods
    
    def query_pan_position(self) -> Optional[float]:
        """
        Query current pan position.
        
        Returns:
            Pan angle in degrees or None if query failed
        """
        logger.debug("Querying pan position")
        self._send_command(self.protocol.query_pan_position())
        time.sleep(0.2)
        response = self._read_response()
        
        if response:
            try:
                parsed = self.protocol.parse_response(response)
                if parsed and parsed['type'] == 'pan_position':
                    return parsed['angle']
            except Exception as e:
                logger.error(f"Error parsing pan position response: {e}")
        
        return None
    
    def query_tilt_position(self) -> Optional[float]:
        """
        Query current tilt position.
        
        Returns:
            Tilt angle in degrees or None if query failed
        """
        logger.debug("Querying tilt position")
        self._send_command(self.protocol.query_tilt_position())
        time.sleep(0.2)
        response = self._read_response()
        
        if response:
            try:
                parsed = self.protocol.parse_response(response)
                if parsed and parsed['type'] == 'tilt_position':
                    return parsed['angle']
            except Exception as e:
                logger.error(f"Error parsing tilt position response: {e}")
        
        return None
    
    def query_position(self) -> Tuple[Optional[float], Optional[float]]:
        """
        Query current pan and tilt position.
        
        Returns:
            Tuple of (pan_angle, tilt_angle) in degrees
        """
        pan = self.query_pan_position()
        tilt = self.query_tilt_position()
        return (pan, tilt)
    
    def get_relative_position(self) -> Tuple[Optional[float], Optional[float], Optional[float], Optional[float]]:
        """
        Get position relative to home position.
        
        Returns:
            Tuple of (relative_pan, relative_tilt, absolute_pan, absolute_tilt)
        """
        abs_pan, abs_tilt = self.query_position()
        
        if abs_pan is None or abs_tilt is None:
            return None, None, abs_pan, abs_tilt
        
        rel_pan = abs_pan
        rel_tilt = abs_tilt
        
        if self.home_pan is not None and self.home_tilt is not None:
            rel_pan = abs_pan - self.home_pan
            rel_tilt = abs_tilt - self.home_tilt
        
        return rel_pan, rel_tilt, abs_pan, abs_tilt
    
    def set_home_position(self) -> bool:
        """
        Set current position as home position.
        
        Returns:
            True if home position was set successfully, False otherwise
        """
        pan, tilt = self.query_position()
        if pan is not None and tilt is not None:
            self.home_pan = pan
            self.home_tilt = tilt
            logger.info(f"Home position set to Pan: {pan:.2f}°, Tilt: {tilt:.2f}°")
            return True
        
        logger.error("Failed to set home position: could not query current position")
        return False
    
    # Absolute position methods
    
    def absolute_pan(self, angle: float) -> bool:
        """
        Move to absolute pan angle.
        
        Args:
            angle: Target pan angle in degrees
            
        Returns:
            True if command was sent successfully, False otherwise
        """
        logger.info(f"Moving to absolute pan angle: {angle:.2f}°")
        return self._send_command(self.protocol.absolute_pan(angle))
    
    def absolute_tilt(self, angle: float) -> bool:
        """
        Move to absolute tilt angle.
        
        Args:
            angle: Target tilt angle in degrees
            
        Returns:
            True if command was sent successfully, False otherwise
        """
        logger.info(f"Moving to absolute tilt angle: {angle:.2f}°")
        return self._send_command(self.protocol.absolute_tilt(angle))
    
    def absolute_position(self, pan: Optional[float] = None, tilt: Optional[float] = None) -> bool:
        """
        Move to absolute position.
        
        Args:
            pan: Target pan angle in degrees or None to skip
            tilt: Target tilt angle in degrees or None to skip
            
        Returns:
            True if commands were sent successfully, False otherwise
        """
        result = True
        
        if pan is not None:
            result = result and self.absolute_pan(pan)
        
        if tilt is not None:
            result = result and self.absolute_tilt(tilt)
        
        return result
    
    # Preset methods
    
    def set_preset(self, preset_id: int) -> bool:
        """
        Set current position as a preset.
        
        Args:
            preset_id: Preset ID (typically 1-255)
            
        Returns:
            True if command was sent successfully, False otherwise
        """
        logger.info(f"Setting preset {preset_id}")
        return self._send_command(self.protocol.set_preset(preset_id))
    
    def call_preset(self, preset_id: int) -> bool:
        """
        Move to a preset position.
        
        Args:
            preset_id: Preset ID (typically 1-255)
            
        Returns:
            True if command was sent successfully, False otherwise
        """
        logger.info(f"Calling preset {preset_id}")
        return self._send_command(self.protocol.call_preset(preset_id))
    
    def clear_preset(self, preset_id: int) -> bool:
        """
        Clear a preset position.
        
        Args:
            preset_id: Preset ID (typically 1-255)
            
        Returns:
            True if command was sent successfully, False otherwise
        """
        logger.info(f"Clearing preset {preset_id}")
        return self._send_command(self.protocol.clear_preset(preset_id))
    
    # Auxiliary methods
    
    def aux_on(self, aux_id: int) -> bool:
        """
        Turn on auxiliary device.
        
        Args:
            aux_id: Auxiliary device ID
            
        Returns:
            True if command was sent successfully, False otherwise
        """
        logger.info(f"Turning on auxiliary {aux_id}")
        return self._send_command(self.protocol.aux_on(aux_id))
    
    def aux_off(self, aux_id: int) -> bool:
        """
        Turn off auxiliary device.
        
        Args:
            aux_id: Auxiliary device ID
            
        Returns:
            True if command was sent successfully, False otherwise
        """
        logger.info(f"Turning off auxiliary {aux_id}")
        return self._send_command(self.protocol.aux_off(aux_id))
    
    # Optical methods
    
    def zoom_in(self) -> bool:
        """
        Zoom in.
        
        Returns:
            True if command was sent successfully, False otherwise
        """
        logger.info("Zooming in")
        return self._send_command(self.protocol.zoom_in())
    
    def zoom_out(self) -> bool:
        """
        Zoom out.
        
        Returns:
            True if command was sent successfully, False otherwise
        """
        logger.info("Zooming out")
        return self._send_command(self.protocol.zoom_out())
    
    def focus_far(self) -> bool:
        """
        Focus far.
        
        Returns:
            True if command was sent successfully, False otherwise
        """
        logger.info("Focusing far")
        return self._send_command(self.protocol.focus_far())
    
    def focus_near(self) -> bool:
        """
        Focus near.
        
        Returns:
            True if command was sent successfully, False otherwise
        """
        logger.info("Focusing near")
        return self._send_command(self.protocol.focus_near())
    
    def iris_open(self) -> bool:
        """
        Open iris.
        
        Returns:
            True if command was sent successfully, False otherwise
        """
        logger.info("Opening iris")
        return self._send_command(self.protocol.iris_open())
    
    def iris_close(self) -> bool:
        """
        Close iris.
        
        Returns:
            True if command was sent successfully, False otherwise
        """
        logger.info("Closing iris")
        return self._send_command(self.protocol.iris_close())
    
    # System methods
    
    def remote_reset(self) -> bool:
        """
        Reset the device.
        
        Returns:
            True if command was sent successfully, False otherwise
        """
        logger.info("Resetting device")
        return self._send_command(self.protocol.remote_reset())
    
    def close(self) -> bool:
        """
        Close the connection to the device.
        
        Returns:
            True if connection was closed successfully, False otherwise
        """
        logger.info("Closing connection")
        return self.connection.close()
    
    def __enter__(self):
        """Support for context manager"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up resources when context manager exits"""
        self.close()
