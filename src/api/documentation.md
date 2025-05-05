# API Module Documentation

The `src/api` module provides the REST and WebSocket API for controlling the Pan-Tilt mount system. It's built using Flask and Flask-SocketIO to offer both HTTP endpoints and real-time communication.

## Files Overview

### `__init__.py`

This file defines the public interface of the API module, exporting the following components:
- `create_app`: Flask application factory
- `register_routes`: Function to register API routes
- Data models: `PositionResponse`, `MovementRequest`, `AbsolutePositionRequest`

### `server.py`

Provides the Flask application factory and server setup functionality:

- `create_app(config, socketio_mode)`: Creates and configures a Flask application with SocketIO support
  - `config`: Optional dictionary with API configuration
  - `socketio_mode`: SocketIO async mode ('threading', 'eventlet', 'gevent')
  - Returns: Tuple of (app, socketio) objects

- `run_app(app, socketio, host, port, debug, use_reloader)`: Runs the Flask application with SocketIO support
  - `app`: Flask application instance
  - `socketio`: SocketIO instance
  - `host`: Host address to listen on (default: '127.0.0.1')
  - `port`: Port to listen on (default: 5000)
  - `debug`: Enable debug mode (default: False)
  - `use_reloader`: Enable auto-reloading (default: False)

### `models.py`

Defines data models for API requests and responses using Python dataclasses:

#### Request Models:

- `MovementRequest`: Request model for directional movement controls
  - `direction`: Direction to move ('up', 'down', 'left', 'right', 'stop')
  - `speed`: Movement speed (0-0x3F, default: 0x20)
  - `validate()`: Validates the request parameters

- `AbsolutePositionRequest`: Request model for absolute position control
  - `pan`: Absolute pan angle (optional)
  - `tilt`: Absolute tilt angle (optional)
  - `validate()`: Validates the request parameters

- `StepPositionRequest`: Request model for incremental position changes
  - `step_pan`: Pan angle change (optional)
  - `step_tilt`: Tilt angle change (optional)
  - `validate()`: Validates the request parameters

#### Response Models:

- `PositionResponse`: Response model for position queries
  - `rel_pan`: Pan angle relative to home position
  - `rel_tilt`: Tilt angle relative to home position
  - `raw_pan`: Raw pan angle (hardware units)
  - `raw_tilt`: Raw tilt angle (hardware units)
  - `status`: Optional status information
  - `to_dict()`: Converts to dictionary for JSON serialization

- `ErrorResponse`: Standard error response model
  - `message`: Error message
  - `code`: HTTP status code (default: 500)
  - `to_dict()`: Converts to dictionary for JSON serialization

- `SuccessResponse`: Standard success response model
  - `message`: Success message
  - `data`: Optional data payload
  - `to_dict()`: Converts to dictionary for JSON serialization

### `routes.py`

Defines the API endpoints and WebSocket events for controlling the pan-tilt mount:

#### Command Processing:

- `process_command_queue()`: Processes queued commands to avoid overlapping operations
- `queue_command(cmd_func, *args, callback=None, **kwargs)`: Adds a command to the queue

#### Main Function:

- `register_routes(app, socketio, controller)`: Registers all API routes and WebSocket events
  - `app`: Flask application instance
  - `socketio`: SocketIO instance
  - `controller`: PTZ controller instance

#### REST API Endpoints:

- `GET /api/device/info`: Get information about the connected device
- `POST /api/device/stop`: Stop all mount movement
- `GET /api/device/position`: Get current position relative to home position
- `POST /api/device/position/absolute`: Move to absolute position
- `POST /api/device/position/step`: Move by incremental step size (deprecated, not used by GUI)
- `POST /api/device/move`: Move at specified speed in a given direction (continuous movement)
- `POST /api/device/home`: Set home position
- `POST /api/device/reset`: Reset the device

#### WebSocket Events:

- `connect`: Handles client connection and sends initial position
- `disconnect`: Handles client disconnection
- `request_position`: Handles position update requests
- `position_update`: Emitted periodically with current position (automatic)

The module also includes a background thread that periodically emits position updates to all connected clients based on the configured polling rate.

## Movement Control Methods

### Continuous Movement API

The preferred method for controlling camera movement is through the continuous movement API:

```
POST /api/device/move
{
  "direction": "up|down|left|right|stop",
  "speed": 16  // Integer between 1-63
}
```

This endpoint provides smooth, continuous movement while the command is active. The camera will continue moving until a stop command is sent.

### Absolute Positioning API

For precise positioning to specific angles:

```
POST /api/device/position/absolute
{
  "pan": 90.0,  // Pan angle in degrees (0-360)
  "tilt": 15.0  // Tilt angle in degrees (-45 to +45)
}
```

This endpoint allows positioning the camera at exact coordinates.

### Step Movement API

> Note: This API is maintained for backward compatibility but is not used by the GUI.

```
POST /api/device/position/step
{
  "step_pan": 1.0,  // Pan angle step in degrees
  "step_tilt": -1.0  // Tilt angle step in degrees
}
```

This endpoint moves the camera by relative increments from the current position.