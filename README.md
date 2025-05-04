# BIT-CCTV Pan-Tilt Control System

A comprehensive control system for BIT-CCTV pan-tilt equipment, enabling precise positioning through multiple interfaces. This system provides complete control over professional-grade PT mounts using the Pelco D protocol, with support for both hardware and simulated devices.

## Overview

This project implements a modular architecture for controlling pan-tilt mounts, with particular focus on the BIT-PT850 heavy-duty unit. The system can be used in several ways:

- **Client-Server Mode**: Run the API server and connect with the GUI client
- **Direct Control**: Use the controller programmatically in your own applications 
- **Development/Testing**: Use the simulator for development without physical hardware

## Features

- **Complete Pelco D Protocol Implementation**: Full support for all movement, position, and auxiliary commands
- **Flexible Connection Options**: Serial (RS-485/RS-422) and Network connections with fallback options
- **RESTful API and WebSockets**: Control via HTTP endpoints with real-time position updates
- **Intuitive PyQt5 GUI**: User-friendly interface with visual feedback and safety features
- **Absolute Positioning**: Precise positioning using angle coordinates (pan 0-360°, tilt -45° to +45°)
- **Preset Management**: Save, recall, and clear multiple position presets
- **Hardware Simulation**: Develop and test without physical hardware using the built-in simulator
- **Advanced Error Handling**: Comprehensive error recovery and diagnostic capabilities
- **Detailed Logging**: Configurable logging system with component-specific logs

## Hardware Support

### BIT-PT850 50kg Heavy Duty Pan Tilt Unit

- Maximum load capacity: 50kg (110.23lb)
- Pan angle: 0-360° continuous rotation
- Tilt angle: -45° to +45° 
- Pan speed: 0.01°/s to 30°/s
- Tilt speed: 0.01°/s to 15°/s
- Preset accuracy: ±0.1°
- IP66 rated for outdoor use

### Other Compatible Hardware

Any pan-tilt equipment that supports the Pelco D protocol should be compatible with this system.

## Installation

### Prerequisites

- Python 3.6 or higher
- PyQt5 (for GUI)
- pyserial (for serial connections)
- Flask and Flask-SocketIO (for API server)
- PyYAML (for configuration)

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/bit-cctv-control.git
   cd bit-cctv-control
   ```

2. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure your settings:
   ```bash
   cp config/settings.example.yaml config/settings.yaml
   # Edit config/settings.yaml with your device settings
   ```

## Project Structure

The project follows a modular, layered architecture:

```
project/
├── config/                 # Configuration files
├── docs/                   # Documentation files
├── gui/                    # PyQt5 GUI implementation
│   ├── main_window_api.py  # Main window with API client
│   ├── control_panel.py    # Control widgets
│   └── ...                 # Other GUI components
├── src/                    # Core implementation
│   ├── api/                # REST and WebSocket API
│   ├── connection/         # Physical connection interfaces
│   ├── controller/         # Command coordination and processing
│   ├── protocol/           # Protocol implementation (Pelco D)
│   └── utils/              # Configuration and helper functions
├── gui_client.py           # GUI client entry point
├── ptz_server.py           # API server entry point
├── run_all.py              # Combined server/client launcher
├── serial_tester.py        # Serial connection tester
├── simple_demo.py          # Protocol simulator demo
└── log_processor.py        # Log analysis utility
```

## Usage

### Option 1: All-in-One Application

Run both the server and GUI client in a single command:

```bash
python run_all.py
```

This script:
- Starts the PTZ server in the background
- Launches the GUI client that connects to the server
- Sets up proper logging for all components
- Handles graceful shutdown when the application closes

### Option 2: Separate Server and Client

Start the API server:

```bash
python ptz_server.py
```

Then start the GUI client in a separate terminal:

```bash
python gui_client.py
```

### Option 3: Direct Control via Python API

Use the controller directly in your Python code:

```python
from src.controller import PTZController
from src.utils import load_config, get_connection_config

config = load_config()
conn_config = get_connection_config(config)

# Using context manager for automatic cleanup
with PTZController(conn_config, address=1) as controller:
    # Query position
    pan, tilt = controller.query_position()
    print(f"Current position: Pan={pan}°, Tilt={tilt}°")
    
    # Move to a position
    controller.absolute_pan(90)
    controller.absolute_tilt(30)
```

### Testing and Diagnostics

The project includes several utilities for testing and diagnostics:

#### Serial Tester

Verify your hardware connection with a simple diagnostic:

```bash
python serial_tester.py --port COM3 --baud 9600
```

This will:
1. Open the serial connection to the device
2. Run the zero-point initialization
3. Query the position multiple times
4. Report results and close the connection

#### Simulator Demo

Test the protocol without hardware:

```bash
python simple_demo.py
```

This demonstrates the protocol simulator with various commands.

#### Log Processing

Parse and analyze log files:

```bash
python log_processor.py your_logfile.log
```

This utility separates logs by component and produces statistics about the log content.

## API Reference

### REST Endpoints

- `GET /api/device/info` - Get device information
- `POST /api/device/stop` - Stop all movement
- `GET /api/device/position` - Get current position
- `POST /api/device/position/absolute` - Move to absolute position
- `POST /api/device/position/step` - Move by incremental step
- `POST /api/device/home` - Set home position
- `POST /api/device/reset` - Reset the device

### WebSocket Events

- `connect` - Client connection handling
- `disconnect` - Client disconnection handling
- `request_position` - Position request event
- `position_update` - Position update notification (emitted periodically)

## Configuration

The system is configured through a YAML file with the following sections:

```yaml
connection:
  port: COM3            # Serial port for device
  baudrate: 9600        # Communication speed
  timeout: 1.0          # Serial timeout in seconds
  retries: 3            # Number of retries for failed commands
  retry_delay: 0.5      # Delay between retries in seconds
  polling_rate: 0.5     # Position update rate in seconds
  enable_polling: true  # Enable automatic position polling

controller:
  address: 1            # Device address (1-255)
  protocol: pelco_d     # Protocol type
  default_speed: 25     # Default movement speed (0-63)
  timeout: 1.0          # Command timeout in seconds

api:
  host: 127.0.0.1       # API server host
  port: 5000            # API server port
  debug: false          # Enable Flask debug mode

client:
  host: localhost       # API server host to connect to
  port: 5000            # API server port to connect to

logging:
  root_level: INFO                      # Default log level
  log_dir: logs                         # Log directory
  file_output: true                     # Enable file logging
  loggers:                              # Logger-specific levels
    ptz_server: INFO
    api_client: INFO
    serial_connection: DEBUG
  patterns:                             # Pattern-based log levels
    "*.serial_*": DEBUG
    "*": INFO
```

## Component Integration

The system is composed of several tightly integrated components:

### Server Component (`ptz_server.py`)

The server component:
- Loads configuration from the YAML file
- Initializes the PTZ controller with the appropriate connection
- Sets up the Flask/SocketIO API server
- Handles zero-point initialization in a background thread
- Provides graceful shutdown with proper resource cleanup

### GUI Client (`gui_client.py`)

The GUI client:
- Connects to the API server using the configured host/port
- Provides a PyQt5-based user interface for controlling the device
- Shows real-time position updates via WebSocket connection
- Implements safety checks and user-friendly controls

### Integration Runner (`run_all.py`)

The integration runner:
- Launches both server and client components as separate processes
- Sets up proper logging with component-specific log levels
- Ensures proper process management and graceful shutdown
- Handles output routing and error detection

### Utilities

Several utilities help with testing and maintenance:

- `serial_tester.py`: Tests the serial connection to the device
- `simple_demo.py`: Demonstrates the simulator with manual protocol commands
- `log_processor.py`: Processes log files into component-specific streams

## Troubleshooting

### Connection Issues

- If the specified COM port is unavailable, the controller will attempt to use the simulator.
- Verify baudrate and protocol settings match your device (typically 9600 baud for BIT-CCTV).
- Run `serial_tester.py` to diagnose connection problems.

### Position Querying Issues

- Some devices require additional configuration to enable position feedback.
- Verify the device supports the Pelco D position query commands.
- Increase the timeout value if the device responds slowly.

### GUI Client Connection Problems

- Ensure the server is running before starting the client.
- Check that the server host/port in the client configuration matches the server.
- Look for firewall or access restrictions if connecting remotely.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- BIT-CCTV for hardware specifications
- Pelco for protocol documentation
