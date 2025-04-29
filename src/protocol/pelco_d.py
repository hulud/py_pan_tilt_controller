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
    Implementation of the Pelco D protocol for pan-tilt unit control.
    
    The Pelco D protocol uses the following message format:
    [0xFF, address, command1, command2, data1, data2, checksum]
    
    Where:
    - 0xFF is the sync byte
    - address is the device address (1-255)
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
            address: Device address (1-255), defaults to 1
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
        Parse a Pelco D response message from the BIT-CCTV pan-tilt mount.
                                         
        BIT-CCTV format (observed): XX 59 DATA1 DATA2 SUM (for pan position)
                                 or XX 5B DATA1 DATA2 SUM (for tilt position)
        
        Where XX is a varying byte that doesn't affect interpretation.

        Args:
            data: Response bytes from the pan-tilt mount

        Returns:
            Dictionary with parsed response data, or None if parsing failed.
        """
        try:
            # Guard against empty data
            if not data:
                logger.warning("Empty response data received")
                return None
                
            hex_data = ' '.join(f'{b:02X}' for b in data)
            logger.debug(f"Parsing response: {hex_data}")

            # Verify expected 5-byte length
            if len(data) != 5:
                logger.warning(f"Unexpected message length: {len(data)}, expected 5 bytes")
                return None
                
            # BIT-CCTV 5-byte format parsing
            try:
                # Ignore first byte, use second byte to determine type
                cmd_byte = data[1]
                data1 = data[2]
                data2 = data[3]
                checksum = data[4]
                
                # Verify custom checksum (cmd + data1 + data2)
                calculated_checksum = (cmd_byte + data1 + data2) % 256
                # BIT-CCTV devices sometimes add 1 to the checksum
                checksum_valid = (calculated_checksum == checksum or calculated_checksum + 1 == checksum)
                
                if not checksum_valid:
                    logger.warning(f"Checksum mismatch in 5-byte format: calculated 0x{calculated_checksum:02X}, got 0x{checksum:02X}")
                    # Continue processing despite checksum mismatch
                
                # Pan position response
                if cmd_byte == self.CMD_PAN_POSITION_RESPONSE:
                    raw_value = (data1 << 8) | data2
                    pan_angle_0_360 = (raw_value / 100.0) % 360.0
                    
                    # Convert to -180 to 180 range
                    pan_angle = pan_angle_0_360
                    if pan_angle > 180.0:
                        pan_angle -= 360.0
                    
                    logger.debug(f"Pan position: raw=0x{data1:02X}{data2:02X}={raw_value}, angle={pan_angle:.2f}°")
                    return {
                        'type': 'pan_position',
                        'angle': pan_angle,
                        'raw': raw_value,
                        'valid': True
                    }
                    
                # Tilt position response
                elif cmd_byte == self.CMD_TILT_POSITION_RESPONSE:
                    raw_value = (data1 << 8) | data2
                    # Calculate tilt angle using Pelco D formula
                    if raw_value > 18000:
                        tilt_angle = ((36000 - raw_value) / 100.0)  # Positive angle
                    else:
                        tilt_angle = -(raw_value / 100.0)  # Negative angle
                        
                    logger.debug(f"Tilt position: raw=0x{data1:02X}{data2:02X}={raw_value}, angle={tilt_angle:.2f}°")
                    return {
                        'type': 'tilt_position',
                        'angle': tilt_angle,
                        'raw': raw_value,
                        'valid': True
                    }
                    
                else:
                    logger.warning(f"Unknown command byte: 0x{cmd_byte:02X}")
                    return None
                    
            except IndexError as e:
                logger.warning(f"Index error while parsing response: {e}, data: {hex_data}")
                return None
                
        except Exception as e:
            logger.warning(f"Unexpected error parsing response: {e}, data: {data.hex() if data else 'None'}")
            return None

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
