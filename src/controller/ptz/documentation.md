# PTZ Controller Module Documentation

This document provides detailed information about the PTZ controller implementation in the Pan-Tilt Control System.

## File Structure

- **`src/controller/__init__.py`**: Package initialization that re-exports the `PTZController` class for easier imports.

- **`src/controller/ptz/__init__.py`**: Subpackage initialization that maintains backward compatibility with the original import path.

- **`src/controller/ptz/core.py`**: Contains the main `PTZController` class implementation which handles all PTZ operations.

## PTZController Class (core.py)

The `PTZController` class is the primary interface for controlling the pan-tilt mount. It provides the following functionality:

### Initialization and Connection

- **`__init__(connection_config, address)`**: Creates a controller instance with the specified connection settings and device address.
  - `connection_config`: Dictionary containing connection parameters (port, baudrate, etc.)
  - `address`: Device address (default: 1)

- **`_create_connection(cfg)`**: Factory method that creates the appropriate connection type (serial or simulator) based on configuration.
  - Handles explicit simulator requests via "SIMULATOR" port name
  - Falls back to simulator if serial connection fails
  - Returns a ConnectionBase subclass instance

- **`close()`**: Properly closes the connection to the device.
  - Ensures the serial port is released
  - Includes delay to allow OS to fully release resources

### Device Movement Commands

- **`stop()`**: Stops all movement.
  - Sends immediate stop command to halt all axes

- **`move_up(speed)`**: Moves the mount upward at the specified speed.
  - `speed`: Movement speed (0x00-0x3F)

- **`move_down(speed)`**: Moves the mount downward at the specified speed.
  - `speed`: Movement speed (0x00-0x3F)

- **`move_left(speed)`**: Pans the mount left at the specified speed.
  - `speed`: Movement speed (0x00-0x3F)

- **`move_right(speed)`**: Pans the mount right at the specified speed.
  - `speed`: Movement speed (0x00-0x3F)

- **`absolute_pan(angle)`**: Moves to an absolute pan position.
  - `angle`: Pan angle in degrees (0-360)

- **`absolute_tilt(angle)`**: Moves to an absolute tilt position.
  - `angle`: Tilt angle in degrees (-90 to +90)

### Position Management

- **`query_pan_position()`**: Queries the current pan angle in degrees.
  - Returns 0.0 on error rather than raising exceptions
  - Handles protocol compatibility for different naming conventions

- **`query_tilt_position()`**: Queries the current tilt angle in degrees.
  - Returns 0.0 on error rather than raising exceptions
  - Handles protocol compatibility for different naming conventions

- **`query_position()`**: Returns both pan and tilt angles as a tuple.
  - Returns `(pan_angle, tilt_angle)` in degrees

- **`get_relative_position()`**: Gets the current position relative to the stored zero points.
  - Returns:
    - `rel_pan_ang` (float): Pan angle relative to zero point
    - `rel_tilt_ang` (float): Tilt angle relative to zero point
    - `status` (dict): Validity flags for the readings

- **`set_home_position()`**: Initializes the zero-point reference for both pan and tilt axes.
  - Sends zero-point commands to the hardware
  - Saves current position as software zero reference
  - Used during initialization to calibrate the system

### Preset Management

- **`set_preset(preset_id)`**: Saves the current position as a preset.
  - `preset_id`: Identifier for the preset position

- **`call_preset(preset_id)`**: Moves to a saved preset position.
  - `preset_id`: Identifier for the preset position to recall

- **`clear_preset(preset_id)`**: Deletes a saved preset.
  - `preset_id`: Identifier for the preset position to clear

### Additional Camera Functions

- **`zoom_in()`**: Activates zoom in functionality.

- **`zoom_out()`**: Activates zoom out functionality.

- **`focus_far()`**: Adjusts focus farther.

- **`focus_near()`**: Adjusts focus nearer.

- **`iris_open()`**: Opens the camera iris.

- **`iris_close()`**: Closes the camera iris.

- **`aux_on(aux_id)`**: Turns on an auxiliary device.
  - `aux_id`: Identifier for the auxiliary device

- **`aux_off(aux_id)`**: Turns off an auxiliary device.
  - `aux_id`: Identifier for the auxiliary device

- **`remote_reset()`**: Resets the device.

### Utility and Implementation Details

- **`_send_command(frame)`**: Internal method to send byte frames to the connection.
  - `frame`: Byte sequence containing the protocol-specific command

- **`connection_type`**: Property that returns the class name of the active connection.
  - Useful for debugging and status reporting

- Context manager support via `__enter__` and `__exit__` methods for proper resource management.

- Protocol compatibility shims that handle differences in function naming between protocol versions.

- Graceful error handling that returns reasonable default values instead of raising exceptions during normal operation.

## Usage Examples

### Basic Initialization and Movement

```python
from src.controller import PTZController
from src.utils import get_connection_config, load_config

# Load configuration
config = load_config()
conn_config = get_connection_config(config)

# Initialize controller
controller = PTZController(conn_config, address=1)

# Perform movement operations
controller.move_up(speed=0x10)  # Move up at medium speed
controller.stop()               # Stop movement
controller.absolute_pan(90)     # Move to 90-degree pan position

# Clean up resources
controller.close()
```

### Using Context Manager

```python
from src.controller import PTZController
from src.utils import get_connection_config, load_config

config = load_config()
conn_config = get_connection_config(config)

# Using context manager for automatic cleanup
with PTZController(conn_config, address=1) as controller:
    # Query position
    pan, tilt = controller.query_position()
    print(f"Current position: Pan={pan}°, Tilt={tilt}°")
    
    # Save current position as preset 1
    controller.set_preset(1)
    
    # Move to a different position
    controller.absolute_pan(180)
    controller.absolute_tilt(30)
    
    # Return to saved preset
    controller.call_preset(1)
# Connection automatically closed when exiting the with block
```

### Relative Position Example

```python
from src.controller import PTZController
from src.utils import get_connection_config, load_config

config = load_config()
conn_config = get_connection_config(config)

controller = PTZController(conn_config, address=1)

# Get position relative to home position
rel_pan, rel_tilt, status = controller.get_relative_position()

if status['pan_valid'] and status['tilt_valid']:
    print(f"Position relative to home: Pan={rel_pan}°, Tilt={rel_tilt}°")
else:
    print("Warning: Invalid position readings")

controller.close()
```

## Common Issues and Troubleshooting

### Connection Problems

- If the specified COM port is not available, the controller will attempt to fall back to a simulator connection.
- Check that the baudrate in the configuration matches the device requirements.
- Ensure the correct protocol is selected for your device (currently focused on Pelco-D).

### Position Querying Issues

- If position queries return 0.0, check that the device supports position feedback.
- Some devices require additional configuration to enable position feedback.
- Verify that the timeout values are appropriate for your device's response time.

### Zero-Point Initialization

- If zero-point initialization fails, the system will use default zero points (0, 0).
- Some devices require specific sequences or timing for proper zero-point calibration.
- Manual calibration can be performed by repositioning the device and calling `set_home_position()`.
