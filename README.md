# Pan-Tilt Camera Control System

A comprehensive control system for Pelco-D compatible pan-tilt camera platforms with step-based motion control and direct positioning capabilities.

## Table of Contents

- [Overview](#overview)
- [System Architecture](#system-architecture)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Running the System](#running-the-system)
- [API Reference](#api-reference)
- [GUI Application](#gui-application)
- [Configuration](#configuration)
- [Step-Based Movement](#step-based-movement)
- [Troubleshooting](#troubleshooting)
- [Development](#development)

## Overview

This system provides a comprehensive interface for controlling pan-tilt camera platforms that use the Pelco-D protocol. Key features include:

- Modular architecture with clear separation of concerns
- Real-time position feedback via WebSockets
- Full implementation of the Pelco-D protocol
- Support for both serial (RS485/RS422) and network connections
- User-friendly GUI with immediate visual feedback
- Step-based motion control for precise positioning
- Direct absolute position control

## System Architecture

The system follows a modular client-server architecture with clearly separated components:

1. **Protocol Layer**: Pure implementation of the Pelco-D protocol
   - Command generation and response parsing
   - Independent of connection methods
   - Comprehensive protocol coverage (movement, presets, positioning)

2. **Connection Layer**: Hardware abstraction layer
   - Supports both serial (RS485/RS422) and network connections
   - Common interface for all connection methods
   - Thread-safe implementation with callback support

3. **Controller Layer**: Business logic
   - Combines protocol and connection layers
   - High-level camera control API
   - Position tracking and home position management

4. **API Layer**: Server middleware
   - REST API endpoints for device control
   - WebSocket for real-time position updates
   - Command queueing to prevent conflicting operations

5. **GUI Layer**: User interface
   - API client with automatic reconnection
   - Real-time position display
   - Safety limits and precise step control

## Project Structure

```
├── config/                      # Configuration files
│   └── settings.yaml            # System configuration
│
├── src/                         # Source code
│   ├── protocol/                # Protocol implementation
│   │   ├── pelco_d.py           # Pelco-D protocol implementation
│   │   ├── commands.py          # Command builders
│   │   └── checksum.py          # Checksum utilities
│   │
│   ├── connection/              # Connection handling
│   │   ├── base.py              # Abstract connection interface
│   │   ├── serial_conn.py       # Serial connection implementation
│   │   └── network_conn.py      # Network connection implementation
│   │
│   ├── controller/              # Controller logic
│   │   └── ptz.py               # Main controller class
│   │
│   ├── api/                     # API implementation
│   │   ├── server.py            # API server implementation
│   │   ├── routes.py            # API route definitions
│   │   └── models.py            # Data models
│   │
│   └── utils/                   # Utility functions
│       └── config.py            # Configuration utilities
│
├── gui/                         # GUI package
│   ├── api_client.py            # Client for API server
│   ├── main_window_api.py       # Main window using API client
│   ├── control_panel.py         # Movement control
│   └── position_display.py      # Position display
│
├── docs/                        # Documentation
│   └── protocol/                # Protocol documentation
│
├── ptz_server.py                # Server startup script
├── gui_client.py                # GUI client script
├── run_all.py                   # Combined script
└── README.md                    # Documentation
```

## Installation

### Prerequisites

- Python 3.6 or higher
- PySerial for hardware communication
- Flask and Flask-SocketIO for the API server
- PyQt5 for the GUI components
- PyYAML for configuration handling

### Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/pan-tilt-controller.git
cd pan-tilt-controller

# Install dependencies
pip install pyserial flask flask-socketio flask-cors python-socketio pyyaml pyqt5
```

### Hardware Requirements

- Pan-tilt camera platform with Pelco-D protocol support
- Serial connection (USB-to-RS485/RS232 adapter) or network connection
- Camera with zoom/focus/iris control (optional)

## Running the System

### Starting the Server

```bash
# Start the API server
python ptz_server.py
```

### Starting the Client

```bash
# Start the GUI client
python gui_client.py
```

### Running Both Components

```bash
# Run both server and client
python run_all.py
```

### Command Line Options

```bash
# Custom configuration file
python ptz_server.py --config my_config.yaml

# Specify host and port
python ptz_server.py --host 192.168.1.100 --port 8080

# Enable debug mode
python ptz_server.py --debug

# Connect client to specific server
python gui_client.py --server http://192.168.1.100:8080
```

## API Reference

### REST API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/device/info` | GET | Device information |
| `/api/device/movement/<direction>` | POST | Control movement |
| `/api/device/position` | GET | Current position |
| `/api/device/position/absolute` | POST | Move to absolute position |
| `/api/device/home` | POST | Set home position |
| `/api/device/presets/<id>` | POST | Set preset |
| `/api/device/presets/<id>/call` | POST | Call preset |
| `/api/device/presets/<id>` | DELETE | Delete preset |
| `/api/device/optical/<action>` | POST | Control optical features |
| `/api/device/aux/<id>` | POST | Control auxiliary devices |
| `/api/device/reset` | POST | Reset device |

### WebSocket Events

| Event | Direction | Description |
|-------|-----------|-------------|
| `connect` | Client → Server | Connect to server |
| `disconnect` | Client → Server | Disconnect from server |
| `request_position` | Client → Server | Request position update |
| `position_update` | Server → Client | Position updated |
| `error` | Server → Client | Error notification |

## GUI Application

The GUI provides an intuitive interface with:

- Real-time position display with relative and absolute coordinates
- Step-size control (0.01° to 10° precision)
- Directional control buttons
- Home position setting
- Connection status indicator
- Immediate movement feedback

## Configuration

Configuration is stored in `config/settings.yaml`:

```yaml
# Connection settings
connection:
  type: serial          # Options: serial, network
  serial:
    port: COM3          # Serial port name (Windows)
    baudrate: 9600      # Communication speed
    data_bits: 8        # Data bits
    stop_bits: 1        # Stop bits
    parity: N           # Parity (N=None, E=Even, O=Odd)
  network:
    ip: 192.168.1.60    # Camera IP address
    port: 80            # Camera port

# Controller settings
controller:
  address: 1            # Camera address (1-255)
  protocol: pelco_d     # Protocol selection
  default_speed: 25     # Default speed (0-63)
  timeout: 1.0          # Response timeout

# API server settings
api:
  host: 127.0.0.1       # Host to bind server
  port: 8080            # Port to listen on
  debug: false          # Debug mode

# Client settings
client:
  host: 127.0.0.1       # Server address 
  port: 8080            # Server port
```

## Step-Based Movement

The system uses step-based movement instead of continuous movement:

1. **Step Size Control**: Specify movement precision (0.01° to 10°)
2. **Directional Control**: Each button press moves by exactly one step
3. **Absolute Positioning**: Direct positioning with 0.01° resolution

## Troubleshooting

### Port Access Issues
- **Problem**: "Socket access forbidden" or "Port already in use" errors
- **Solution**: Use a different port (edit settings.yaml or use --port option)
- **Solution**: Close other applications that might be using the port
- **Solution**: Run with admin/sudo privileges if necessary

### Serial Connection Issues
- **Problem**: "Failed to open serial port" error
- **Solution**: Verify correct COM port in settings.yaml
- **Solution**: Check physical connections and power
- **Solution**: Install proper USB-to-serial drivers
- **Solution**: Verify baudrate matches device (typically 2400/4800/9600)

### API Server Connection Issues
- **Problem**: "Server not found" or connection errors
- **Solution**: Verify server is running (check console output)
- **Solution**: Check port and host match in client and server configurations
- **Solution**: Disable firewall or add exception

### GUI Import Errors
- **Problem**: Import errors when running client script
- **Solution**: Ensure you're running from the project root directory
- **Solution**: Verify all dependencies are installed

### Device Communication Issues
- **Problem**: No response from device
- **Solution**: Check cable connections (RS485 polarity matters)
- **Solution**: Verify device address (default is 1)
- **Solution**: Test with lower baudrate (some devices require 2400 or 4800)

## Development

### Extending the System

The modular architecture makes it easy to extend:

1. **Adding New Protocols**: Create new modules in src/protocol/
2. **Adding New Connection Types**: Implement ConnectionBase interface
3. **Adding New API Endpoints**: Add routes to src/api/routes.py
4. **Adding New GUI Components**: Add widgets to gui/ package

### Custom Configurations

For different environments, create custom config files:

```bash
# Create a custom config
cp config/settings.yaml config/production.yaml

# Edit as needed
# Then run with:
python ptz_server.py --config config/production.yaml
```
