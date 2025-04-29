"""
Command builders for Pelco D protocol.

This module provides functions to generate Pelco D protocol command packets
for various camera operations.
"""
from typing import List, Tuple, Optional
from .checksum import calculate_checksum


def create_basic_command(address: int, cmd1: int, cmd2: int, data1: int, data2: int) -> bytes:
    """
    Create a basic Pelco D command.
    
    Args:
        address: Camera address (1-255)
        cmd1: Command byte 1
        cmd2: Command byte 2
        data1: Data byte 1
        data2: Data byte 2
        
    Returns:
        Command bytes
    """
    # Create message without checksum
    message = [0xFF, address, cmd1, cmd2, data1, data2]
    
    # Calculate and append checksum
    checksum = calculate_checksum(message)
    message.append(checksum)
    
    return bytes(message)


# Movement commands

def create_stop_command(address: int) -> bytes:
    """Create command to stop all movement"""
    return create_basic_command(address, 0x00, 0x00, 0x00, 0x00)


def create_up_command(address: int, speed: int = 0x20) -> bytes:
    """Create command to move up"""
    return create_basic_command(address, 0x00, 0x08, 0x00, speed)


def create_down_command(address: int, speed: int = 0x20) -> bytes:
    """Create command to move down"""
    return create_basic_command(address, 0x00, 0x10, 0x00, speed)


def create_left_command(address: int, speed: int = 0x20) -> bytes:
    """Create command to move left"""
    return create_basic_command(address, 0x00, 0x04, speed, 0x00)


def create_right_command(address: int, speed: int = 0x20) -> bytes:
    """Create command to move right"""
    return create_basic_command(address, 0x00, 0x02, speed, 0x00)


def create_left_up_command(address: int, pan_speed: int = 0x20, tilt_speed: int = 0x20) -> bytes:
    """Create command to move left and up simultaneously"""
    return create_basic_command(address, 0x00, 0x0C, pan_speed, tilt_speed)


def create_left_down_command(address: int, pan_speed: int = 0x20, tilt_speed: int = 0x20) -> bytes:
    """Create command to move left and down simultaneously"""
    return create_basic_command(address, 0x00, 0x14, pan_speed, tilt_speed)


def create_right_up_command(address: int, pan_speed: int = 0x20, tilt_speed: int = 0x20) -> bytes:
    """Create command to move right and up simultaneously"""
    return create_basic_command(address, 0x00, 0x0A, pan_speed, tilt_speed)


def create_right_down_command(address: int, pan_speed: int = 0x20, tilt_speed: int = 0x20) -> bytes:
    """Create command to move right and down simultaneously"""
    return create_basic_command(address, 0x00, 0x12, pan_speed, tilt_speed)


# Preset commands

def create_set_preset_command(address: int, preset_id: int) -> bytes:
    """Create command to set a preset position"""
    return create_basic_command(address, 0x00, 0x03, 0x00, preset_id)


def create_call_preset_command(address: int, preset_id: int) -> bytes:
    """Create command to call a preset position"""
    return create_basic_command(address, 0x00, 0x07, 0x00, preset_id)


def create_clear_preset_command(address: int, preset_id: int) -> bytes:
    """Create command to clear a preset position"""
    return create_basic_command(address, 0x00, 0x05, 0x00, preset_id)


# Query commands

def create_pan_position_query(address: int) -> bytes:
    """Create command to query pan position"""
    return create_basic_command(address, 0x00, 0x51, 0x00, 0x00)


def create_tilt_position_query(address: int) -> bytes:
    """Create command to query tilt position"""
    return create_basic_command(address, 0x00, 0x53, 0x00, 0x00)


# Absolute position commands

def create_pan_absolute_command(address: int, angle: float) -> bytes:
    """
    Create command to move to absolute pan position.
    
    Args:
        address: Camera address (1-255)
        angle: Target angle in degrees (-180 to 180)
        
    Returns:
        Command bytes
    """
    # Normalize angle to 0-360 range
    if angle < 0:
        # Convert negative angle to equivalent positive angle
        angle = 360 + angle
    
    # Convert angle to data value (angle * 100)
    value = int(angle * 100)
    data1 = (value >> 8) & 0xFF  # High byte
    data2 = value & 0xFF         # Low byte
    
    return create_basic_command(address, 0x00, 0x4B, data1, data2)


def create_tilt_absolute_command(address: int, angle: float) -> bytes:
    """
    Create command to move to absolute tilt position.
    
    Args:
        address: Camera address (1-255)
        angle: Target angle in degrees
        
    Returns:
        Command bytes
    """
    if angle < 0:
        # Negative angle
        value = int(abs(angle) * 100)
    else:
        # Positive angle
        value = 36000 - int(angle * 100)
    
    data1 = (value >> 8) & 0xFF  # High byte
    data2 = value & 0xFF         # Low byte
    
    return create_basic_command(address, 0x00, 0x4D, data1, data2)


# Auxiliary commands

def create_aux_on_command(address: int, aux_id: int) -> bytes:
    """Create command to turn auxiliary on"""
    return create_basic_command(address, 0x00, 0x09, 0x00, aux_id)


def create_aux_off_command(address: int, aux_id: int) -> bytes:
    """Create command to turn auxiliary off"""
    return create_basic_command(address, 0x00, 0x0B, 0x00, aux_id)


# Zero point setting commands

def create_set_pan_zero_point_command(address: int) -> bytes:
    """Create command to set pan zero point"""
    return create_basic_command(address, 0x00, 0x03, 0x00, 0x67)


def create_set_tilt_zero_point_command(address: int) -> bytes:
    """Create command to set tilt zero point"""
    return create_basic_command(address, 0x00, 0x03, 0x00, 0x68)


# Reset and default commands

def create_remote_reset_command(address: int) -> bytes:
    """Create command to reset the device"""
    return create_basic_command(address, 0x00, 0x0F, 0x00, 0x00)


# Optical commands (zoom, focus, iris)

def create_zoom_in_command(address: int) -> bytes:
    """Create command to zoom in"""
    return create_basic_command(address, 0x00, 0x20, 0x00, 0x00)


def create_zoom_out_command(address: int) -> bytes:
    """Create command to zoom out"""
    return create_basic_command(address, 0x00, 0x40, 0x00, 0x00)


def create_focus_far_command(address: int) -> bytes:
    """Create command to focus far"""
    return create_basic_command(address, 0x00, 0x80, 0x00, 0x00)


def create_focus_near_command(address: int) -> bytes:
    """Create command to focus near"""
    return create_basic_command(address, 0x01, 0x00, 0x00, 0x00)


def create_iris_open_command(address: int) -> bytes:
    """Create command to open iris"""
    return create_basic_command(address, 0x02, 0x00, 0x00, 0x00)


def create_iris_close_command(address: int) -> bytes:
    """Create command to close iris"""
    return create_basic_command(address, 0x04, 0x00, 0x00, 0x00)
