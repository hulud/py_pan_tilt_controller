# Protocol Module Documentation

## Overview

The `protocol` module implements the communication protocols used for controlling Pan-Tilt-Zoom (PTZ) cameras. The primary focus is on the Pelco D protocol, which is a standard protocol for PTZ camera control over serial connections.

This documentation covers the key components, their relationships, and usage patterns of the protocol module.

## Files Overview

| Filename | Purpose |
|----------|---------|
| `__init__.py` | Module initialization, exposes public API |
| `checksum.py` | Utilities for calculating and validating Pelco D checksums |
| `commands.py` | Functions to generate Pelco D protocol command packets |
| `pelco_d.py` | Core implementation of the Pelco D protocol |
| `pelco_parser.py` | Parser for BIT-CCTV's custom Pelco D response format |
| `pan_tilt_pelco_d_protocol.csv` | Reference documentation of protocol commands |

## Module Structure

The protocol module follows a layered design:

1. **Low-level utilities**: Checksum calculation and validation
2. **Command builders**: Functions for creating specific protocol messages
3. **Protocol implementation**: Main class that encapsulates protocol behavior
4. **Response parsing**: Specialized parsers for device responses

## Protocol Details

### Pelco D Protocol Format

The Pelco D protocol uses a 7-byte message format:

```
[0xFF, address, command1, command2, data1, data2, checksum]
```

Where:
- `0xFF` is the sync byte
- `address` is the device address (1-255)
- `command1`, `command2` are command bytes
- `data1`, `data2` are data bytes
- `checksum` is the sum of all bytes except the sync byte, modulo 256

### BIT-CCTV Response Format

The BIT-CCTV devices use a custom 5-byte response format:

```
[XX, command, data1, data2, checksum]
```

Where:
- `XX` is a variable byte that doesn't affect interpretation
- `command` identifies the response type (e.g., 0x59 for pan position, 0x5B for tilt position)
- `data1`, `data2` contain the response data
- `checksum` is calculated as (command + data1 + data2) modulo 256, sometimes +1

## Key Components

### Checksum Module (`checksum.py`)

Provides two key functions:

- `calculate_checksum(message)`: Calculates the Pelco D checksum for a message
- `validate_checksum(message)`: Validates the checksum of a complete Pelco D message

Usage example:
```python
from protocol.checksum import calculate_checksum, validate_checksum

# Calculate checksum for a message
message = [0xFF, 0x01, 0x00, 0x08, 0x00, 0x20]
checksum = calculate_checksum(message)  # Returns 0x29

# Validate a complete message
complete_msg = [0xFF, 0x01, 0x00, 0x08, 0x00, 0x20, 0x29]
is_valid = validate_checksum(complete_msg)  # Returns True
```

### Commands Module (`commands.py`)

Provides functions to generate various Pelco D commands:

- **Movement commands**: stop, up, down, left, right, diagonal movements
- **Preset commands**: set, call, clear presets
- **Query commands**: pan position, tilt position
- **Absolute position commands**: move to specific pan/tilt angles
- **Auxiliary commands**: turn on/off auxiliary devices
- **Zero point commands**: set pan/tilt zero points
- **Optical commands**: zoom, focus, iris control

All command functions follow a consistent pattern:

```python
from protocol.commands import create_up_command, create_pan_absolute_command

# Create command to move up at speed 32 (0x20)
up_cmd = create_up_command(address=1, speed=0x20)  # Returns bytes object

# Create command to move to absolute pan position (45 degrees)
pan_cmd = create_pan_absolute_command(address=1, angle=45.0)  # Returns bytes object
```

### Pelco D Protocol Class (`pelco_d.py`)

The `PelcoDProtocol` class encapsulates the protocol behavior:

- Initializes with device address
- Provides methods for all supported commands
- Handles message creation with proper checksums
- Parses device responses

Usage example:
```python
from protocol.pelco_d import PelcoDProtocol

# Create protocol handler for device at address 1
protocol = PelcoDProtocol(address=1)

# Generate command to move right at speed 32
move_cmd = protocol.move_right(speed=0x20)

# Parse a response from the device
response_data = b'\x00\x59\x00\x64\xBD'  # Example response
parsed = protocol.parse_response(response_data)
if parsed and parsed['type'] == 'pan_position':
    print(f"Pan angle: {parsed['angle']} degrees")
```

### Pelco Parser (`pelco_parser.py`)

Provides specialized functions for parsing BIT-CCTV's custom Pelco D response format:

- `parse_response(response)`: Parses a 5-byte response and extracts position information
- `format_command(cmd_bytes)`: Formats command bytes for human-readable logging
- Additional utility functions for common commands

Usage example:
```python
from protocol.pelco_parser import parse_response, create_pan_query

# Create a query command
query_cmd = create_pan_query(address=1)

# Parse response
response = b'\x00\x59\x00\x64\xBD'  # Example response
result = parse_response(response)
print(f"Position: {result['position_formatted']}")  # "Position: 1.00°"
```

## Protocol Reference

The `pan_tilt_pelco_d_protocol.csv` file contains a reference for Pelco D commands and responses:

- Command names and descriptions
- Message formats for both directions (PC→Device, Device→PC)
- Example messages
- Format variable descriptions

Key commands include:
- Horizontal/Vertical Angle Query
- Horizontal/Vertical Angle Control
- Movement commands (Stop, Up, Down, Left, Right)
- Setting horizontal/vertical origin points

## Integration with Controller

The protocol module is typically used by a controller class that handles:

1. Serial communication with the device
2. Command sequencing and timing
3. Response handling and error recovery
4. Position tracking and reporting

Example integration:
```python
from protocol.pelco_d import PelcoDProtocol
from serial import Serial

class PTZController:
    def __init__(self, port, address=1):
        self.serial = Serial(port, 9600, timeout=1)
        self.protocol = PelcoDProtocol(address)
    
    def move_right(self, speed=32):
        cmd = self.protocol.move_right(speed)
        self.serial.write(cmd)
    
    def get_pan_position(self):
        cmd = self.protocol.query_pan_position()
        self.serial.write(cmd)
        response = self.serial.read(5)  # Read 5-byte response
        parsed = self.protocol.parse_response(response)
        return parsed['angle'] if parsed else None
```

## Extending the Protocol Module

### Adding New Commands

To add a new command:

1. Add the command builder function to `commands.py`
2. Add the corresponding method to `PelcoDProtocol` class in `pelco_d.py`
3. Update the `__init__.py` exports if the command should be part of the public API

### Adding New Protocols

To add support for a new protocol (e.g., Pelco P):

1. Create a new file (e.g., `pelco_p.py`) implementing the protocol
2. Create a corresponding command builder file if needed
3. Update `__init__.py` to expose the new protocol

## Debugging and Troubleshooting

The protocol module includes extensive logging to help with debugging:

- Command creation and validation
- Response parsing and interpretation
- Checksum validation
- Error conditions

Example debugging output:
```
DEBUG:protocol.pelco_d:Parsing response: 00 59 00 64 BD
DEBUG:protocol.pelco_d:Pan position: raw=0x0064=100, angle=1.00°
DEBUG:protocol.pelco_parser:Command: Address: 1, Command: 00 51, Data: 00 00, Checksum: 52 ✓ | Type: QUERY | Pan Position Query
```
