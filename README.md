# Pan-Tilt Camera Control System

A comprehensive control system for Pelco-D compatible pan-tilt camera platforms with step-based motion control and direct positioning capabilities.

## Table of Contents

- [Overview](#overview)
- [System Architecture](#system-architecture)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Running the System](#running-the-system)
- [API Reference](#api-reference)
  - [REST API Endpoints](#rest-api-endpoints)
  - [WebSocket Events](#websocket-events)
- [GUI Application](#gui-application)
- [Configuration](#configuration)
- [Step-Based Movement](#step-based-movement)
- [Troubleshooting](#troubleshooting)

## Overview

This system provides a comprehensive interface for controlling pan-tilt camera platforms that use the Pelco-D protocol. Key features include:

- Structured architecture with API server middleware
- Real-time position feedback via WebSockets
- Full implementation of the Pelco-D protocol
- User-friendly GUI with immediate visual feedback
- Step-based motion control for precise positioning
- Direct absolute position control
- Support for presets, cruising, scanning, and other advanced features

## System Architecture

The system follows a client-server architecture with three main components:

1. **API Server**: Acts as middleware between clients and devices
   - REST API endpoints for device control
   - WebSocket support for real-time updates
   - Handles device communication protocol details

2. **GUI Client**: User interface that communicates with API server
   - Connects to API server via HTTP and WebSockets
   - Provides intuitive control interface with step-based motion
   - Displays real-time position data
   - Allows direct absolute positioning

3. **Device Layer**: Hardware communication
   - Implements Pelco-D protocol over serial connection
   - Handles direct device control via RS-485/RS-232

This architecture provides several advantages:
- Separation of concerns between UI, business logic, and device communication
- Multiple clients can connect to a single device
- Improved maintainability with modular components

## Project Structure

```
├── api_server.py              # API server middleware
├── config.yaml                # System configuration file
│
├── pelco_D/                   # API package for hardware control
│   ├── __init__.py            # Package exports
│   ├── controller.py          # Main controller class with serial communication
│   ├── position.py            # Position tracking and querying functions
│   ├── movement.py            # Basic movement commands (up/down/left/right)
│   ├── absolute_position.py   # Absolute positioning commands
│   ├── presets.py             # Preset position management
│   ├── auxiliary.py           # Auxiliary device controls
│   ├── optical.py             # Camera lens controls (zoom/focus/iris)
│   └── advanced.py            # Advanced features (cruise/scan/guard)
│
├── gui/                       # GUI package
│   ├── __init__.py            # Package exports
│   ├── app.py                 # Application entry point
│   ├── api_client.py          # Client for communicating with API server
│   ├── main_window_api.py     # Main window using API client
│   ├── main_window.py         # Main window (for direct device control)
│   ├── control_panel.py       # Movement control buttons with step control
│   └── position_display.py    # Position indicator widgets
│
├── pan_tilt_gui.py            # Original GUI launcher (direct device control)
├── pan_tilt_gui_api.py        # API-based GUI launcher
└── README.md                  # This documentation file
```

## Installation

### Prerequisites

- Python 3.6 or higher
- PyQt5 for the GUI components
- pyserial for serial communication
- Flask, Flask-SocketIO, and Flask-CORS for the API server
- python-socketio for the GUI client
- PyYAML for configuration handling

### Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/pan-tilt-controller.git
cd pan-tilt-controller

# Install dependencies
pip install pyqt5 pyserial flask flask-socketio flask-cors python-socketio pyyaml
```

### Hardware Requirements

- Pan-tilt camera platform with Pelco-D protocol support
- Serial connection (USB-to-RS485/RS232 adapter)
- Camera with appropriate lens

## Running the System

### Starting the API Server

```bash
# Start the API server
python api_server.py
```

The server will start on http://127.0.0.1:5000 by default. You can change the host and port in the config.yaml file.

### Launching the GUI Client

```bash
# Launch the GUI client
python pan_tilt_gui_api.py
```

The client will automatically connect to the API server at http://localhost:5000.

### Command Line Options

```bash
# Specifying a different API server
python pan_tilt_gui_api.py --server http://other-server:5000

# Specifying host and port separately
python pan_tilt_gui_api.py --host 192.168.1.100 --port 8080
```

## API Reference

### REST API Endpoints

The API server provides the following endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/device/info` | GET | Get information about the device |
| `/api/device/movement/<direction>` | POST | Control movement (up/down/left/right/stop) |
| `/api/device/position` | GET | Get current position |
| `/api/device/position/absolute` | POST | Move to absolute position |
| `/api/device/home` | POST | Set current position as home |
| `/api/device/presets` | GET | Get available presets |
| `/api/device/presets/<id>` | POST | Set a preset |
| `/api/device/presets/<id>/call` | POST | Call a preset |
| `/api/device/presets/<id>` | DELETE | Delete a preset |
| `/api/device/optical/<action>` | POST | Control optical features (zoom/focus/iris) |
| `/api/device/aux/<id>` | POST | Control auxiliary devices |
| `/api/device/cruise/<action>` | POST | Control cruise functions |

### WebSocket Events

The API server supports the following WebSocket events:

| Event | Direction | Description |
|-------|-----------|-------------|
| `connect` | Client → Server | Establish connection |
| `disconnect` | Client → Server | Close connection |
| `request_position` | Client → Server | Request current position update |
| `position_update` | Server → Client | Receive position updates |
| `error` | Server → Client | Error notifications |

## GUI Application

The GUI application provides an intuitive interface for controlling the pan-tilt device:

- **Connection Status**: Visual indicator for API server connection
- **Position Display**: Shows current pan/tilt position relative to home
- **Step Size Control**: Specifies the angle increment for each button press (0.01° to 10° precision)
- **Directional Controls**: Buttons for incremental movement in specific directions
- **Home Position**: Set the current position as the reference point
- **Absolute Position Controls**: Direct input of pan and tilt angles for precise positioning

## Configuration

The system configuration is stored in `config.yaml`:

```yaml
# Server settings (for the API server to listen on)
server:
  host: 127.0.0.1   # Listen on loopback interface only
  port: 5000        # Default API server port

# Client settings (for the GUI to connect to)
client:
  host: localhost   # Server address for client to connect to
  port: 5000        # Should match server port

# Device configuration
device:
  port: COM3        # Serial port for real device
  baudrate: 9600    # Serial baudrate
  address: 1        # Device address (1-255)
  blocking: false   # Whether to wait for movements to complete
  timeout: 1.0      # Serial timeout in seconds
```

## Step-Based Movement

The system uses step-based movement instead of continuous speed-based motion:

1. **Step Size Control**
   - Specify the size of each movement step in degrees (0.01° to 10° range)
   - High precision control with 0.01° resolution
   - Maximum step size limited to 10° for safety and control
   - Each button press moves the camera by exactly this amount
   - Provides precise positioning for accurate camera alignment

2. **Directional Control**
   - UP/DOWN: Increments/decrements tilt by step size
   - LEFT/RIGHT: Increments/decrements pan by step size 
   - STOP: Immediately stops all movement

3. **Absolute Positioning**
   - Direct input of exact pan and tilt angles
   - High precision with 0.01° resolution
   - Moves directly to the specified coordinates

## Troubleshooting

### Connection Issues
- Verify the API server is running (`python api_server.py`)
- Check server address and port in the client configuration
- Ensure no firewall is blocking the connection
- Verify the server and client are on the same network or localhost

### Device Communication Problems
- Check if the device is powered on and properly connected
- Verify the correct COM port is selected in config.yaml
- Ensure proper baudrate settings (typically 2400, 4800, or 9600)
- Check physical connections and wiring (most systems use RS-485)
- Verify the correct device address is used (default is 1)

### Serial Port Issues
- Make sure the serial port is not in use by another application
- Check that you have the correct permissions to access the port
- On Linux/Mac, make sure your user is in the appropriate group (e.g., 'dialout')
- Try using a different USB port if using a USB-to-serial adapter
- Verify that the correct drivers are installed for your adapter

### GUI Problems
- Verify PyQt5 and other dependencies are properly installed
- Check for error messages in the console
- Restart the application if the GUI becomes unresponsive
