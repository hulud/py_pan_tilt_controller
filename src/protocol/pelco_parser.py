"""
BIT-CCTV Pelco-D Protocol Parser

This module handles the custom 5-byte response format used by BIT-CCTV cameras
when responding to standard Pelco-D commands.
"""
import binascii
import logging

logger = logging.getLogger(__name__)

# Standard Pelco-D command codes
CMD_PAN_POSITION_QUERY = bytes.fromhex("00 51")
CMD_TILT_POSITION_QUERY = bytes.fromhex("00 53")
CMD_PAN_ABSOLUTE = bytes.fromhex("00 4B")
CMD_TILT_ABSOLUTE = bytes.fromhex("00 4D")
CMD_STOP = bytes.fromhex("00 00")
CMD_UP = bytes.fromhex("00 08")
CMD_DOWN = bytes.fromhex("00 10")
CMD_RIGHT = bytes.fromhex("00 02")
CMD_LEFT = bytes.fromhex("00 04")
CMD_SET_PRESET = bytes.fromhex("00 03")
CMD_CALL_PRESET = bytes.fromhex("00 07")
CMD_CLEAR_PRESET = bytes.fromhex("00 05")

# Response identifiers
RESP_PAN_POSITION = 0x59
RESP_TILT_POSITION = 0x5B


def calculate_checksum(data):
    """Calculate Pelco-D checksum: sum of all bytes after the sync byte, lower 8 bits"""
    return sum(data) & 0xFF


def create_command(address, command, data1, data2):
    """Create a Pelco-D command with the correct checksum"""
    cmd_bytes = [0xFF, address, command[0], command[1], data1, data2]
    checksum = calculate_checksum(cmd_bytes[1:])
    cmd_bytes.append(checksum)
    return bytes(cmd_bytes)


def create_pan_query(address=1):
    """Create a pan position query command"""
    return create_command(address, CMD_PAN_POSITION_QUERY, 0, 0)


def create_tilt_query(address=1):
    """Create a tilt position query command"""
    return create_command(address, CMD_TILT_POSITION_QUERY, 0, 0)


def create_absolute_pan_command(address, angle):
    """Create command to move to absolute pan angle
    
    Args:
        address: Device address
        angle: Target angle in degrees
        
    Returns:
        Command bytes
    """
    # Convert angle to raw value (angle * 100)
    raw_value = int(angle * 100)
    data1 = (raw_value >> 8) & 0xFF
    data2 = raw_value & 0xFF
    return create_command(address, CMD_PAN_ABSOLUTE, data1, data2)


def create_absolute_tilt_command(address, angle):
    """Create command to move to absolute tilt angle
    
    Args:
        address: Device address
        angle: Target angle in degrees (positive = up, negative = down)
        
    Returns:
        Command bytes
    """
    # Convert angle to raw value using Pelco-D formula
    if angle >= 0:
        # Positive angle: 36000 - (angle * 100)
        raw_value = 36000 - int(angle * 100)
    else:
        # Negative angle: abs(angle) * 100
        raw_value = int(abs(angle) * 100)
    
    data1 = (raw_value >> 8) & 0xFF
    data2 = raw_value & 0xFF
    return create_command(address, CMD_TILT_ABSOLUTE, data1, data2)


def create_stop_command(address=1):
    """Create a stop movement command"""
    return create_command(address, CMD_STOP, 0, 0)


def parse_response(response):
    """Parse BIT-CCTV's custom 5-byte Pelco-D response format
    
    Args:
        response: 5-byte response from camera
        
    Returns:
        Dictionary with parsed response information
    """
    if not response or len(response) != 5:
        logger.warning(f"Invalid response length: {len(response) if response else 0}, expected 5 bytes")
        return {
            'valid': False, 
            'error': f"Invalid response length: {len(response) if response else 0}"
        }
    
    # Unpack the 5-byte response
    byte1, cmd_byte, data1, data2, checksum = response
    
    # Basic response info
    result = {
        'valid': True,
        'raw_bytes': binascii.hexlify(response, ' ').decode().upper(),
        'cmd_byte': cmd_byte,
        'data_bytes': [data1, data2],
        'checksum': checksum,
    }
    
    # Verify checksum (BIT-CCTV appears to use cmd + data1 + data2, sometimes +1)
    calculated_checksum = (cmd_byte + data1 + data2) % 256
    result['calculated_checksum'] = calculated_checksum
    result['checksum_valid'] = (calculated_checksum == checksum or calculated_checksum + 1 == checksum)
    
    # Interpret based on command byte
    if cmd_byte == RESP_PAN_POSITION:
        position = (data1 * 256 + data2) / 100.0
        result['type'] = 'pan_position'
        result['position'] = position
        result['position_formatted'] = f"{position:.2f}°"
    
    elif cmd_byte == RESP_TILT_POSITION:
        tdata = (data1 * 256 + data2)
        if tdata > 18000:
            tangle = (36000 - tdata) / 100.0
            result['position_type'] = 'positive'
        else:
            tangle = -tdata / 100.0
            result['position_type'] = 'negative'
        
        result['type'] = 'tilt_position'
        result['position'] = tangle
        result['position_formatted'] = f"{tangle:.2f}°"
    
    else:
        result['type'] = 'unknown'
    
    return result


def format_command(cmd_bytes):
    """Format command bytes for logging"""
    address = cmd_bytes[1]
    cmd1, cmd2 = cmd_bytes[2], cmd_bytes[3]
    data1, data2 = cmd_bytes[4], cmd_bytes[5]
    checksum = cmd_bytes[6]
    
    cmd_type = "UNKNOWN"
    details = ""
    
    # Identify command type
    if cmd1 == 0x00 and cmd2 == 0x51:
        cmd_type = "QUERY"
        details = "Pan Position Query"
    elif cmd1 == 0x00 and cmd2 == 0x53:
        cmd_type = "QUERY"
        details = "Tilt Position Query"
    elif cmd1 == 0x00 and cmd2 == 0x4B:
        cmd_type = "ABSOLUTE"
        angle = (data1 * 256 + data2) / 100.0
        details = f"Pan Absolute Position: {angle:.2f}°"
    elif cmd1 == 0x00 and cmd2 == 0x4D:
        cmd_type = "ABSOLUTE"
        tdata = (data1 * 256 + data2)
        if tdata > 18000:
            tangle = (36000 - tdata) / 100.0
            details = f"Tilt Absolute Position: +{tangle:.2f}°"
        else:
            tangle = -tdata / 100.0
            details = f"Tilt Absolute Position: {tangle:.2f}°"
    elif cmd1 == 0x00 and cmd2 == 0x00:
        cmd_type = "MOVEMENT"
        details = "Stop"
    elif cmd1 == 0x00 and cmd2 == 0x02:
        cmd_type = "MOVEMENT"
        details = f"Right (Speed: {data1})"
    elif cmd1 == 0x00 and cmd2 == 0x04:
        cmd_type = "MOVEMENT"
        details = f"Left (Speed: {data1})"
    elif cmd1 == 0x00 and cmd2 == 0x08:
        cmd_type = "MOVEMENT"
        details = f"Up (Speed: {data2})"
    elif cmd1 == 0x00 and cmd2 == 0x10:
        cmd_type = "MOVEMENT"
        details = f"Down (Speed: {data2})"
    elif cmd1 == 0x00 and cmd2 == 0x03:
        cmd_type = "PRESET"
        if data2 == 0x67:
            details = "Set Pan Zero Point"
        elif data2 == 0x68:
            details = "Set Tilt Zero Point"
        else:
            details = f"Set Preset {data2}"
    elif cmd1 == 0x00 and cmd2 == 0x07:
        cmd_type = "PRESET"
        details = f"Call Preset {data2}"
    elif cmd1 == 0x00 and cmd2 == 0x05:
        cmd_type = "PRESET"
        details = f"Delete Preset {data2}"
    
    # Calculate own checksum for verification
    calculated = calculate_checksum(cmd_bytes[1:6])
    checksum_valid = "✓" if calculated == checksum else "✗"
    
    return f"Address: {address}, Command: {cmd1:02X} {cmd2:02X}, Data: {data1:02X} {data2:02X}, Checksum: {checksum:02X} {checksum_valid} | Type: {cmd_type} | {details}"
