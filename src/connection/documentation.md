# Connection Module Documentation

This document provides detailed information about the connection module in the PTZ Camera Control System.

## Overview

The `connection` module provides various implementations for communication with PTZ cameras through different physical interfaces. All implementations share a common interface defined by the `ConnectionBase` abstract class.

## Files Structure

1. `__init__.py` - Module initialization and exports
2. `base.py` - Abstract base class defining the connection interface
3. `serial_conn.py` - Serial communication implementation over RS-485/RS-422
4. `simulator_connection.py` - Simulation implementation for testing without hardware
5. `network_conn.py` - Network communication implementation over TCP/IP

## Detailed Documentation

### `__init__.py`

**Purpose**: Initializes the connection module and exports the key classes.

**Exports**:
- `ConnectionBase` - Abstract base class for all connection types
- `SerialConnection` - Implementation for serial (RS-485/RS-422) communication
- `SimulatorConnection` - Implementation for simulated hardware testing

### `base.py`

**Purpose**: Defines the abstract interface that all connection implementations must follow.

**Key Components**:

- `ConnectionBase` (Abstract Class): The foundation for all connection types with the following abstract methods:
  - `open()` - Opens the connection to the device
  - `close()` - Closes the connection to the device
  - `is_open()` - Checks if the connection is currently open
  - `send(data)` - Sends data to the device
  - `receive(size, timeout)` - Receives data from the device
  - `receive_until(terminator, max_size, timeout)` - Receives data until a specific terminator
  - `config` property - Gets the current connection configuration
  - `set_config(config)` - Updates the connection configuration
  - `register_receive_callback(callback)` - Registers a callback for data reception
  - `unregister_receive_callback()` - Unregisters the data reception callback

**Usage Example**:
```python
# This class cannot be instantiated directly but serves as a template
# for concrete implementations
```

### `serial_conn.py`

**Purpose**: Provides a concrete implementation of the `ConnectionBase` for serial connections to PTZ cameras.

**Key Components**:

- `SerialConnection` (Class): Implements serial communication over RS-485/RS-422 interfaces.
  - Handles opening and closing of serial ports with retry logic
  - Manages data transmission and reception
  - Provides command parsing and debugging for Pelco-D protocol
  - Supports asynchronous data reception through callbacks

**Constructor Parameters**:
- `port` (str): Serial port name (e.g., 'COM3', '/dev/ttyUSB0')
- `baudrate` (int): Communication speed (default: 9600)
- `data_bits` (int): Number of data bits (default: 8)
- `stop_bits` (int): Number of stop bits (default: 1)
- `parity` (str): Parity checking ('N', 'E', 'O', 'M', 'S') (default: 'N')
- `timeout` (float): Read timeout in seconds (default: 1.0)
- `polling_rate` (float): Rate for polling position updates (default: None)
- `enable_polling` (bool): Enable/disable position polling (default: True)

**Special Features**:
- Detailed logging of serial communications with Pelco-D command interpretation
- Error handling and recovery for serial port access issues
- Thread safety with mutex locking for I/O operations
- Support for exclusive mode to prevent port conflicts

**Usage Example**:
```python
from src.connection import SerialConnection

# Create serial connection
conn = SerialConnection(port='COM3', baudrate=9600)

# Open the connection
if conn.open():
    try:
        # Send Pelco-D command
        pan_right_cmd = bytes([0xFF, 0x01, 0x00, 0x02, 0x20, 0x00, 0x23])
        conn.send(pan_right_cmd)
        
        # Receive response
        response = conn.receive(size=5, timeout=1.0)
        print(f"Received: {response.hex()}")
    finally:
        # Close the connection
        conn.close()
```

### `simulator_connection.py`

**Purpose**: Provides a simulated connection for testing without physical hardware.

**Key Components**:

- `SimulatorConnection` (Class): Simulates a PTZ camera connection for development and testing.
  - Emulates responses to Pelco-D protocol commands
  - Maintains internal state of camera position
  - Processes commands in a background thread

- `PelcoDDeviceState` (Class): Maintains the state of the simulated PTZ device.
  - Tracks pan and tilt positions
  - Handles zero-point calibration
  - Converts between raw position values and angles

**Special Features**:
- Accurate simulation of device behavior including response timing
- Command parsing and appropriate responses for position queries
- Support for absolute positioning commands
- Zero-point calibration command support

**Usage Example**:
```python
from src.connection import SimulatorConnection

# Create simulator connection
sim = SimulatorConnection()

# Open the connection
if sim.open():
    try:
        # Send pan position query command
        query_cmd = bytes([0xFF, 0x01, 0x00, 0x51, 0x00, 0x00, 0x52])
        sim.send(query_cmd)
        
        # Receive simulated response
        response = sim.receive(timeout=1.0)
        print(f"Received: {response.hex()}")
    finally:
        # Close the connection
        sim.close()
```

### `network_conn.py`

**Purpose**: Provides a concrete implementation of the `ConnectionBase` for network connections to PTZ cameras.

**Key Components**:

- `NetworkConnection` (Class): Implements TCP/IP communication with network-capable PTZ cameras.
  - Manages socket connections
  - Handles data transmission and reception over networks
  - Provides timeout and error handling

**Constructor Parameters**:
- `ip` (str): Camera IP address (default: '192.168.1.60')
- `port` (int): Camera TCP port (default: 80)
- `timeout` (float): Connection timeout in seconds (default: 1.0)

**Special Features**:
- Non-blocking I/O with select-based timeout handling
- Support for terminator-based reception
- Asynchronous data reception through callbacks
- Graceful connection handling and cleanup

**Usage Example**:
```python
from src.connection import NetworkConnection

# Create network connection
conn = NetworkConnection(ip='192.168.1.100', port=8080)

# Open the connection
if conn.open():
    try:
        # Send command
        cmd = b'GET /ptz/control?pan=90&tilt=0 HTTP/1.1\r\nHost: camera\r\n\r\n'
        conn.send(cmd)
        
        # Receive response until HTTP end marker
        response = conn.receive_until(b'\r\n\r\n', timeout=2.0)
        print(f"Received: {response.decode('ascii')}")
    finally:
        # Close the connection
        conn.close()
```

## Best Practices

1. **Always use context managers** when possible to ensure proper resource cleanup:
   ```python
   with SerialConnection() as conn:
       conn.send(command)
       response = conn.receive()
   ```

2. **Handle exceptions** from connection operations, especially when dealing with physical hardware:
   ```python
   try:
       conn.send(command)
       response = conn.receive()
   except ConnectionError as e:
       print(f"Connection error: {e}")
   except TimeoutError as e:
       print(f"Timeout error: {e}")
   ```

3. **Use the simulator for testing** to avoid hardware dependencies during development:
   ```python
   # Use simulator for testing
   conn = SimulatorConnection()
   
   # Use real hardware in production
   # conn = SerialConnection(port='COM3')
   ```

4. **Configure timeouts appropriately** based on expected device response times:
   ```python
   # For position queries which should return quickly
   response = conn.receive(timeout=1.0)
   
   # For operations that might take longer
   response = conn.receive(timeout=5.0)
   ```

5. **Use callbacks for asynchronous reception** when continuous monitoring is needed:
   ```python
   def handle_data(data):
       print(f"Received data: {data.hex()}")
   
   conn.register_receive_callback(handle_data)
   # ... later ...
   conn.unregister_receive_callback()
   ```
