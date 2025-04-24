"""
Core implementation of the Pelco D protocol.

This module provides the fundamental functionality for encoding and decoding
Pelco D protocol messages as described in the protocol specification.
"""
from typing import List, Tuple, Optional, Union, Dict, Any
import time
import threading
import logging
from .checksum import calculate_checksum, validate_checksum
from .commands import (
    create_stop_command,
    create_up_command,
    create_down_command,
    create_left_command,
    create_right_command,
    create_left_up_command,
    create_left_down_command,
    create_right_up_command,
    create_right_down_command,
    create_set_preset_command,
    create_call_preset_command,
    create_clear_preset_command,
    create_pan_position_query,
    create_tilt_position_query,
    create_pan_absolute_command,
    create_tilt_absolute_command,
    create_aux_on_command,
    create_aux_off_command,
    create_set_pan_zero_point_command,
    create_set_tilt_zero_point_command,
    create_remote_reset_command,
    create_zoom_in_command,
    create_zoom_out_command,
    create_focus_far_command,
    create_focus_near_command,
    create_iris_open_command,
    create_iris_close_command,
)

logger = logging.getLogger(__name__)

class PelcoDProtocol:
    """
    Implementation of the Pelco D protocol for PTZ camera control.
    
    The Pelco D protocol uses the following message format:
    [0xFF, address, command1, command2, data1, data2, checksum]
    
    Where:
    - 0xFF is the sync byte
    - address is the camera address (1-255)
    - command1, command2 are command bytes
    - data1, data2 are data bytes
    - checksum is the sum of all bytes except 0xFF, modulo 256
    """
    
    SYNC_BYTE = 0xFF
    
    # Response commands
    CMD_PAN_POSITION_RESPONSE = 0x59
    CMD_TILT_POSITION_RESPONSE = 0x5B
    
    def __init__(self, address: int = 1):
        """
        Initialize the PelcoD protocol handler.
        
        Args:
            address: Camera address (1-255), defaults to 1
        """
        if not 1 <= address <= 255:
            raise ValueError(f"Address must be between 1 and 255, got {address}")
        
        self.address = address
    
    def create_message(self, cmd1: int, cmd2: int, data1: int, data2: int) -> bytes:
        """
        Create a Pelco D message.
        
        Args:
            cmd1: Command byte 1
            cmd2: Command byte 2
            data1: Data byte 1
            data2: Data byte 2
            
        Returns:
            Bytes object containing the complete Pelco D message
        """
        # Create message without checksum
        message = [self.SYNC_BYTE, self.address, cmd1, cmd2, data1, data2]
        
        # Calculate checksum
        checksum = calculate_checksum(message)
        
        # Add checksum to message
        message.append(checksum)
        
        # Convert to bytes
        return bytes(message)
    
    def parse_response(self, data: bytes) -> Optional[Dict[str, Any]]:
        """
        Parse a response message from the camera.
        
        Args:
            data: Response bytes from the camera
            
        Returns:
            Dictionary with parsed response data or None if parsing failed
        """
        # Validate response format
        if len(data) < 7 or data[0] != self.SYNC_BYTE:
            logger.warning(f"Invalid response format: {data.hex()}")
            return None
        
        # Check for valid checksum
        if not validate_checksum(data):
            logger.warning(f"Invalid checksum in response: {data.hex()}")
            return None
        
        # Extract command type and data
        address = data[1]
        cmd1 = data[2]
        cmd2 = data[3]
        data1 = data[4]
        data2 = data[5]
        
        # Parse based on command type
        if cmd2 == self.CMD_PAN_POSITION_RESPONSE:
            # Parse pan position response
            p_data = (data1 << 8) | data2
            pan_angle = p_data / 100.0
            return {
                'type': 'pan_position',
                'angle': pan_angle
            }
        elif cmd2 == self.CMD_TILT_POSITION_RESPONSE:
            # Parse tilt position response
            t_data = (data1 << 8) | data2
            
            # Convert to angle based on the protocol specification
            if t_data > 18000:
                tilt_angle = (36000 - t_data) / 100.0
            else:
                tilt_angle = -t_data / 100.0
                
            return {
                'type': 'tilt_position',
                'angle': tilt_angle
            }
        else:
            # Unknown response type
            return {
                'type': 'unknown',
                'cmd1': cmd1,
                'cmd2': cmd2,
                'data1': data1,
                'data2': data2
            }
    
    # Movement commands
    
    def stop(self) -> bytes:
        """Stop all movement."""
        return create_stop_command(self.address)
        
    def move_up(self, speed: int = 0x20) -> bytes:
        """Move up at specified speed."""
        return create_up_command(self.address, speed)
        
    def move_down(self, speed: int = 0x20) -> bytes:
        """Move down at specified speed."""
        return create_down_command(self.address, speed)
        
    def move_left(self, speed: int = 0x20) -> bytes:
        """Move left at specified speed."""
        return create_left_command(self.address, speed)
        
    def move_right(self, speed: int = 0x20) -> bytes:
        """Move right at specified speed."""
        return create_right_command(self.address, speed)
        
    def move_left_up(self, pan_speed: int = 0x20, tilt_speed: int = 0x20) -> bytes:
        """Move left and up simultaneously."""
        return create_left_up_command(self.address, pan_speed, tilt_speed)
        
    def move_left_down(self, pan_speed: int = 0x20, tilt_speed: int = 0x20) -> bytes:
        """Move left and down simultaneously."""
        return create_left_down_command(self.address, pan_speed, tilt_speed)
        
    def move_right_up(self, pan_speed: int = 0x20, tilt_speed: int = 0x20) -> bytes:
        """Move right and up simultaneously."""
        return create_right_up_command(self.address, pan_speed, tilt_speed)
        
    def move_right_down(self, pan_speed: int = 0x20, tilt_speed: int = 0x20) -> bytes:
        """Move right and down simultaneously."""
        return create_right_down_command(self.address, pan_speed, tilt_speed)
    
    # Preset commands
    
    def set_preset(self, preset_id: int) -> bytes:
        """Set current position as a preset."""
        return create_set_preset_command(self.address, preset_id)
        
    def call_preset(self, preset_id: int) -> bytes:
        """Move to a preset position."""
        return create_call_preset_command(self.address, preset_id)
        
    def clear_preset(self, preset_id: int) -> bytes:
        """Clear a preset position."""
        return create_clear_preset_command(self.address, preset_id)
    
    # Position query commands
    
    def query_pan_position(self) -> bytes:
        """Generate command to query pan position."""
        return create_pan_position_query(self.address)
        
    def query_tilt_position(self) -> bytes:
        """Generate command to query tilt position."""
        return create_tilt_position_query(self.address)
    
    # Absolute position commands
    
    def absolute_pan(self, angle: float) -> bytes:
        """Generate command to move to absolute pan angle."""
        return create_pan_absolute_command(self.address, angle)
        
    def absolute_tilt(self, angle: float) -> bytes:
        """Generate command to move to absolute tilt angle."""
        return create_tilt_absolute_command(self.address, angle)
    
    # Auxiliary commands
    
    def aux_on(self, aux_id: int) -> bytes:
        """Turn on auxiliary device."""
        return create_aux_on_command(self.address, aux_id)
        
    def aux_off(self, aux_id: int) -> bytes:
        """Turn off auxiliary device."""
        return create_aux_off_command(self.address, aux_id)
    
    # Zero point commands
    
    def set_pan_zero_point(self) -> bytes:
        """Set current pan position as zero point."""
        return create_set_pan_zero_point_command(self.address)
        
    def set_tilt_zero_point(self) -> bytes:
        """Set current tilt position as zero point."""
        return create_set_tilt_zero_point_command(self.address)
    
    # Reset command
    
    def remote_reset(self) -> bytes:
        """Reset the device."""
        return create_remote_reset_command(self.address)
    
    # Optical commands
    
    def zoom_in(self) -> bytes:
        """Zoom in."""
        return create_zoom_in_command(self.address)
        
    def zoom_out(self) -> bytes:
        """Zoom out."""
        return create_zoom_out_command(self.address)
        
    def focus_far(self) -> bytes:
        """Focus far."""
        return create_focus_far_command(self.address)
        
    def focus_near(self) -> bytes:
        """Focus near."""
        return create_focus_near_command(self.address)
        
    def iris_open(self) -> bytes:
        """Open iris."""
        return create_iris_open_command(self.address)
        
    def iris_close(self) -> bytes:
        """Close iris."""
        return create_iris_close_command(self.address)
