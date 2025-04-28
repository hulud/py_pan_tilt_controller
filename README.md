# Pan-Tilt Camera Control System

A comprehensive control system for Pelco-D compatible pan-tilt camera platforms using USB serial connections. The system provides step-based motion control and direct positioning capabilities with a client-server architecture.

## Overview

This system provides a complete interface for controlling pan-tilt camera platforms that use the Pelco-D protocol over serial connections. Key features include:

- USB/Serial connection (RS485/RS422) to camera hardware
- Full implementation of the Pelco-D protocol with enhanced reliability
- Client-server architecture with WebSocket position feedback
- User-friendly GUI with immediate visual feedback
- Step-based motion control for precise positioning
- Direct absolute position control with 0.01° precision
- Enhanced debugging for serial communications

## System Architecture

The system follows a modular client-server architecture:

1. **Protocol Layer**: Implementation of the Pelco-D protocol
   - Command generation and response parsing
   - Robust position feedback interpretation
   - Complete protocol coverage (movement, presets, positioning)
   - Detailed command and response debugging

2. **Serial Connection Layer**: 
   - USB-to-Serial communication (RS485/RS422)
   - Thread-safe implementation with retry mechanisms
   - Error resilient communication
   - Comprehensive debugging of sent and received data

3. **Controller Layer**: 
   - Combines protocol and connection layers
   - High-level camera control API
   - Position tracking and feedback handling
   - Detailed operation logging and status reporting

4. **API Server Layer**: 
   - REST API endpoints for device control (localhost only)
   - WebSocket for real-time position updates
   - Command queueing to prevent conflicting operations

5. **GUI Layer**: 
   - Connection to local API server
   - Real-time position display
   - Intuitive camera controls with step precision

## Hardware Requirements

- Pan-tilt camera platform with Pelco-D protocol support
- USB-to-RS485/RS422 serial adapter
- Compatible camera (optional: with zoom/focus/iris control)

## Installation

### Prerequisites

- Python 3.6 or higher
- PySerial for hardware communication
- Flask and Flask-SocketIO for the API server
- PyQt5 for the GUI components

### Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/pan-tilt-controller.git
cd pan-tilt-controller

# Install dependencies
pip install pyserial flask flask-socketio flask-cors python-socketio pyyaml pyqt5
```

## Configuration

The system configuration is stored in `config/settings.yaml`:

```yaml
connection:
  serial:
    port: COM3  # or /dev/ttyUSB0 for Linux
    baudrate: 9600
    data_bits: 8
    stop_bits: 1
    parity: N

controller:
  address: 1  # Camera address
  protocol: pelco_d
  default_speed: 25  # Default movement speed (0-63)
  timeout: 1.0  # Response timeout in seconds

api:
  host: 127.0.0.1  # Local API server address
  port: 8080
  debug: false

client:
  host: 127.0.0.1  # API server address for client
  port: 8080
```

## Running the System

### Start the API Server

The server handles communication between the GUI and the camera hardware:

```bash
python ptz_server.py
```

### Start the GUI Client

The client provides a user interface to control the camera:

```bash
python gui_client.py
```

### Run Both Components

To start both server and client at once:

```bash
python run_all.py
```

## Command Line Options

```bash
# Custom configuration file
python ptz_server.py --config custom_config.yaml

# Specify different host and port
python ptz_server.py --host 127.0.0.1 --port 9000

# Enable debug mode
python ptz_server.py --debug

# Connect client to specific server
python gui_client.py --server http://127.0.0.1:9000
```

## Features

### Precise Movement Control

- Step-based movement with configurable precision (0.01° to 10°)
- Absolute positioning with direct angle control
- Real-time position feedback (when supported by hardware)
- Home position setting and tracking

### Advanced Capabilities

- Preset position management (save/call/delete)
- Optical controls (zoom/focus/iris) when available
- Auxiliary device control
- Robust error handling and retry mechanisms

### Improved Protocol Implementation

The Pelco D protocol implementation has been enhanced for reliability:
- Robust position feedback parsing with error handling
- Multiple retry mechanisms for position queries
- Enhanced timing for more reliable communication
- Zero-point calibration for accurate positioning

### Enhanced Pelco-D Response Handling

The system now implements strict response parsing based on serial_commands_and_responses.csv:
- Strictly enforces 5-byte message format for position responses (`00 59 HH LL CS` for pan)
- Detailed error reporting for invalid message formats
- Consistent checksum validation for all responses
- Improved error handling with buffer diagnostics

### Comprehensive Debugging

The system includes extensive debugging capabilities for serial communications:
- Detailed hex and ASCII dumps of all sent and received data
- Command structure parsing and validation
- Protocol message decoding with field identification
- Transaction timing and status reporting
- See `docs/DEBUG_IMPROVEMENTS.md` for details

## Recent Changes

### PTZ Controller Improvements (2025-04-28)
- Simplified positioning API by removing raw angle returns from query methods
- Fixed Flask-SocketIO attribute storage for better controller instance management
- Added scaling correction (1/8.22) for more accurate step movements
- Eliminated debug mode auto-reloading to prevent connection issues
- Enhanced error handling with standardized returns instead of exceptions

### Parser Improvements (2025-04-28)
- Fixed redundant code in position reply parser
- Implemented strict 5-byte message format validation
- Added detailed error logging for malformed responses
- Updated message handling to match serial_commands_and_responses.csv specification
- Improved buffer diagnostics for troubleshooting communication issues

## Troubleshooting

### Serial Port Issues

- **Problem**: "Failed to open serial port" error
- **Solution**: Verify correct COM port in settings.yaml
- **Solution**: Check physical connections and power
- **Solution**: Install proper USB-to-serial drivers
- **Solution**: Verify baudrate matches device (typically 2400/4800/9600)

### Permission Issues

- **Problem**: Permission denied accessing USB port
- **Solution**: On Linux, add user to the dialout group: `sudo usermod -a -G dialout $USER`
- **Solution**: On Windows, run with administrator privileges if necessary

### Position Feedback Issues

- **Problem**: Inconsistent or missing position feedback
- **Solution**: The system will gracefully handle missing feedback with estimated positions
- **Solution**: Check that your PTZ device supports position feedback (some don't)
- **Solution**: Try different baudrates if communication is unstable
- **Solution**: Enable debug mode to verify correct 5-byte response format

### Movement Scaling Issues

- **Problem**: Step movements are larger than requested (e.g., 1° in GUI causes 8° actual movement)
- **Solution**: The software now applies a scaling factor to compensate for hardware differences
- **Solution**: Custom scaling can be adjusted in commands.py if needed for different hardware

## Development

The modular architecture makes it easy to extend:

1. **Adding New Protocol Commands**: Extend the commands.py module
2. **Supporting New Cameras**: Update the protocol parameters
3. **Adding New API Endpoints**: Add routes to src/api/routes.py 
4. **Customizing the GUI**: Modify components in the gui/ package