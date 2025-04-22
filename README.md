# Pan-Tilt Camera Control System

A comprehensive control system for Pelco-D compatible pan-tilt camera platforms with enhanced safety features, API server middleware, device simulator, and GUI interface.

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
- [Device Simulator](#device-simulator)
- [Configuration](#configuration)
- [Safety Features](#safety-features)
- [Troubleshooting](#troubleshooting)

## Overview

This system provides a comprehensive interface for controlling pan-tilt camera platforms that use the Pelco-D protocol. Key features include:

- Restructured architecture with API server middleware
- Real-time position feedback via WebSockets
- Virtual device simulator for development and testing
- Full implementation of the Pelco-D protocol with enhanced safety features
- User-friendly GUI with immediate visual feedback
- Position-based safety limits and timeout protection
- Support for presets, cruising, scanning, and other advanced features

## System Architecture

The system follows a client-server architecture with three main components:

1. **API Server**: Acts as middleware between clients and devices
   - REST API endpoints for device control
   - WebSocket support for real-time updates
   - Handles device communication protocol details
   - Supports both real hardware and simulator devices

2. **GUI Client**: User interface that communicates with API server
   - Connects to API server via HTTP and WebSockets
   - Provides intuitive control interface
   - Displays real-time position data
   - Implements safety features and visual feedback

3. **Device Layer**: Hardware communication or simulation
   - Real hardware: Implements Pelco-D protocol over serial connection
   - Simulator: Virtual device that mimics real hardware behavior
   - Compatible interface between both implementations

This architecture provides several advantages:
- Separation of concerns between UI, business logic, and device communication
- Multiple clients can connect to a single device
- Development and testing can occur without physical hardware
- Improved maintainability with modular components

## Project Structure

```
├── api_server.py              # API server middleware
├── device_simulator.py        # Virtual device simulator
├── config.yaml                # System configuration file
│
├── pelco_D_api/               # API package for real hardware control
│   ├── __init__.py            # Package exports
│   ├── controller.py          # Main controller class with serial communication
│   ├── position.py            # Position tracking and querying functions
│   ├── movement.py            # Basic movement commands (up/down/left/right)
│   ├── absolute_position.py   # Absolute positioning with safety overrides
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
│   ├── main_window.py         # Original main window (for direct device control)
│   ├── control_panel.py       # Movement control buttons and safety controls
│   ├── position_display.py    # Position indicator widgets
│   └── safety_indicator.py    # Visual safety limit indicators
│
├── pan_tilt_gui.py            # Original GUI launcher (direct device control)
├── pan_tilt_gui_api.py        # API-based GUI launcher
└── README.md                  # This documentation file
```

## Installation

### Prerequisites

- Python 3.6 or higher
- PyQt5 for the GUI components
- pyserial for serial communication (real hardware only)
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

### Hardware Requirements (for real device operation)

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
- **Directional Controls**: Buttons for movement with visual feedback
- **Home Position**: Set the current position as the reference point
- **Safety Indicators**: Visual feedback for approaching movement limits

## Device Simulator

The device simulator mimics a real pan-tilt device:

- Maintains internal position state (pan and tilt)
- Responds to all commands like a real device
- Simulates movement with realistic timing and acceleration
- Supports presets, home position, and position queries
- Implements the same API as the real device controller

To switch between real hardware and the simulator, modify the `device.type` setting in `config.yaml`:

```yaml
device:
  type: simulator  # Use 'real' for hardware or 'simulator' for virtual device
```

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
  type: simulator   # 'real' for hardware, 'simulator' for virtual device
  port: COM3        # Serial port for real device (ignored by simulator)
  baudrate: 9600    # Serial baudrate (ignored by simulator)
  address: 1        # Device address (1-255)
  blocking: false   # Whether to wait for movements to complete
  timeout: 1.0      # Serial timeout in seconds (ignored by simulator)

# Safety settings
safety:
  limit_degrees: 45.0      # Maximum movement from home position
  warning_threshold: 0.85  # Threshold for warning indicator (0.0-1.0)
  timeout_seconds: 5.0     # Automatic stop after continuous movement
```

## Safety Features

The system implements multiple safety mechanisms:

1. **Movement Limits**
   - Prevents movement beyond 45° from home position in any direction
   - Configurable limit via safety settings

2. **Timeout Protection**
   - Automatically stops movement after 5 seconds of continuous operation
   - Prevents runaway conditions if a button gets stuck

3. **Visual Warnings**
   - Red indicator appears when approaching 85% of movement limits
   - Visual feedback before hard limits are reached

4. **Protected Absolute Positioning**
   - Absolute positioning disabled by default
   - Requires explicit override with warnings about potential risks
   - Position display shows both offset and raw values for clarity

5. **Home Position Reference**
   - All safety calculations use user-defined home position
   - Resets safety limits when home position is changed

## Troubleshooting

### Connection Issues
- Verify the API server is running (`python api_server.py`)
- Check server address and port in the client configuration
- Ensure no firewall is blocking the connection
- Verify the server and client are on the same network or localhost

### Device Communication Problems
- For real hardware:
  - Verify the correct COM port is selected in config.yaml
  - Ensure proper baudrate settings (typically 2400, 4800, or 9600)
  - Check physical connections and wiring (most systems use RS-485)
  - Verify the correct device address is used (default is 1)

### GUI Problems
- Verify PyQt5 and other dependencies are properly installed
- Check for error messages in the console
- Restart the application if the GUI becomes unresponsive

### Simulator Issues
- Restart the API server to reset the simulator state
- Check for error messages in the API server console
- Verify the simulator is selected in config.yaml (`device.type: simulator`)
