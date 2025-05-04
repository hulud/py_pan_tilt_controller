# Pan-Tilt-Zoom (PTZ) Camera Control System Documentation

This documentation provides a comprehensive overview of the PTZ Camera Control System project structure and components.

## Project Architecture

The system follows a layered architecture with the following main components:

1. **API Layer** (`src/api/`) - REST and WebSocket interface for external control
2. **Controller Layer** (`src/controller/`) - Core control logic and command processing
3. **Protocol Layer** (`src/protocol/`) - Implementation of device communication protocols
4. **Connection Layer** (`src/connection/`) - Physical connection abstractions (serial, network)
5. **Utilities** (`src/utils/`) - Configuration and helper functions

## Directory Structure

```
src/
├── api/                  # API implementation
│   ├── __init__.py       # Module initialization
│   ├── models.py         # API data models
│   ├── routes.py         # API endpoints
│   ├── server.py         # Flask server setup
│   └── documentation.md  # API documentation
│
├── connection/           # Connection interfaces
│   ├── __init__.py       # Module initialization
│   ├── base.py           # Abstract base class
│   ├── serial_conn.py    # Serial connection
│   ├── network_conn.py   # Network connection
│   ├── simulator_connection.py # Simulator for testing
│   └── documentation.md  # Connection documentation
│
├── controller/           # Controller layer
│   ├── ptz/              # PTZ specific controller
│   │   ├── __init__.py   # Module initialization
│   │   ├── core.py       # Main PTZ controller class
│   │   └── documentation.md # PTZ controller docs
│   └── __init__.py       # Package initialization
│
├── protocol/             # Protocol implementation
│   ├── __init__.py       # Module initialization
│   ├── checksum.py       # Checksum utilities
│   ├── commands.py       # Protocol command builders
│   ├── pelco_d.py        # Pelco D protocol
│   ├── pelco_parser.py   # Response parser
│   ├── pan_tilt_pelco_d_protocol.csv # Reference data
│   └── documentation.md  # Protocol documentation
│
├── utils/                # Utility functions
│   ├── __init__.py       # Module initialization
│   ├── config.py         # Configuration utilities
│   └── documentation.md  # Utils documentation
│
└── __init__.py           # Package initialization
```

## Component Details

### 1. API Module

The API module provides REST endpoints and WebSocket events for controlling the PTZ system.

#### Key Features:
- RESTful interface for PTZ control
- WebSocket support for real-time position updates
- JSON data models for requests and responses
- Command queuing to prevent operational conflicts

#### Main Endpoints:
- `GET /api/device/info` - Get device information
- `POST /api/device/stop` - Stop all movement
- `GET /api/device/position` - Get current position
- `POST /api/device/position/absolute` - Move to absolute position
- `POST /api/device/home` - Set home position
- `POST /api/device/reset` - Reset the device

#### WebSocket Events:
- `connect` - Client connection handling
- `disconnect` - Client disconnection handling
- `request_position` - Position request event
- `position_update` - Position update notification

### 2. Connection Module

The connection module provides a set of classes for communication with PTZ devices through different physical interfaces.

#### Key Components:
- `ConnectionBase` - Abstract interface defining common connection methods
- `SerialConnection` - RS-485/RS-422 serial communication implementation
- `NetworkConnection` - TCP/IP communication implementation
- `SimulatorConnection` - Simulation implementation for testing

#### Features:
- Unified interface for all connection types
- Error handling and recovery
- Thread safety with mutex locking
- Support for polling and callbacks
- Detailed logging for debugging

### 3. Controller Module

The controller module provides a high-level interface for controlling PTZ devices, abstracting the protocol details.

#### Main Features:
- Device movement control (up, down, left, right)
- Absolute position control (pan and tilt angles)
- Relative position tracking
- Home position calibration
- Preset management
- Additional camera functions (zoom, focus, iris)

#### Implementation:
- Thread-safe command execution
- Connection management
- Error handling and recovery
- Context manager support

### 4. Protocol Module

The protocol module implements the communication protocols used for PTZ camera control, with primary focus on Pelco D.

#### Key Components:
- Message formatting and parsing
- Checksum calculation and validation
- Command builder functions
- Response parsing
- Protocol-specific behavior encapsulation

#### Supported Commands:
- Movement commands (stop, up, down, left, right)
- Preset commands (set, call, clear)
- Query commands (pan/tilt position)
- Absolute position commands
- Auxiliary commands
- Zero point commands
- Optical commands (zoom, focus, iris)

### 5. Utils Module

The utils module provides utility functions for the system, primarily focused on configuration management.

#### Main Functions:
- `load_config()` - Load configuration from YAML file
- `get_connection_config()` - Extract connection configuration
- `get_controller_config()` - Extract controller configuration
- `get_api_config()` - Extract API configuration

## Usage Examples

### Basic System Initialization

```python
from src.controller import PTZController
from src.utils import load_config, get_connection_config
from src.api import create_app, register_routes
from flask_socketio import SocketIO

# Load configuration
config = load_config()
conn_config = get_connection_config(config)

# Initialize controller
controller = PTZController(conn_config, address=1)

# Create Flask application with SocketIO
app, socketio = create_app(config)

# Register API routes
register_routes(app, socketio, controller)

# Run the application
socketio.run(app, host='0.0.0.0', port=5000)
```

### Direct Control Example

```python
from src.controller import PTZController
from src.utils import load_config, get_connection_config

# Load configuration
config = load_config()
conn_config = get_connection_config(config)

# Initialize controller with context manager
with PTZController(conn_config, address=1) as controller:
    # Query current position
    pan, tilt = controller.query_position()
    print(f"Current position: Pan={pan}°, Tilt={tilt}°")
    
    # Move to absolute position
    controller.absolute_pan(90)
    controller.absolute_tilt(30)
    
    # Use relative movement
    controller.move_right(speed=0x20)  # Medium speed
    controller.stop()
```

## Communication Flow

1. **Client → API**: REST/WebSocket requests
2. **API → Controller**: Method calls with parameters
3. **Controller → Protocol**: Command generation
4. **Protocol → Connection**: Binary data transmission
5. **Connection → Device**: Physical transmission
6. **Device → Connection**: Response reception
7. **Connection → Protocol**: Response parsing
8. **Protocol → Controller**: Structured data
9. **Controller → API**: Response models
10. **API → Client**: JSON/WebSocket responses

## Design Patterns

- **Layered Architecture**: Clear separation of concerns
- **Adapter Pattern**: Connection classes adapt physical interfaces
- **Factory Method**: Connection creation based on configuration
- **Command Pattern**: Protocol command encapsulation
- **Observer Pattern**: Position update notifications
- **Strategy Pattern**: Different protocol implementations

## Best Practices

1. **Error Handling**: All layers include error handling with appropriate fallbacks
2. **Resource Management**: Context managers ensure proper cleanup
3. **Thread Safety**: Critical sections are protected with locks
4. **Configuration**: External configuration for all components
5. **Testing Support**: Simulator implementation for testing without hardware

## Development and Extension

1. **Adding New Protocols**: Implement a new protocol class following the existing pattern
2. **Supporting New Hardware**: Add a new connection class implementing ConnectionBase
3. **Adding API Endpoints**: Update the routes.py file with new endpoints
4. **Extending Controller**: Add new methods to the PTZController class
