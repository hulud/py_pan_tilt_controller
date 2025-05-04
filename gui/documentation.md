# GUI Module Documentation

## Overview

The `gui` module provides a PyQt5-based graphical user interface for the PTZ Camera Control System. It enables users to interact with pan-tilt-zoom cameras through a clean interface that communicates with the backend server API.

## Architecture

The GUI follows a client-server architecture:

- **Client**: PyQt5-based interface that communicates with the server via HTTP and WebSockets
- **Server**: Flask-SocketIO server implementing the control API (outside this module)

### Key Components

| Component | Description |
|-----------|-------------|
| `MainWindowAPI` | Main application window that coordinates all GUI components |
| `APIClient` | Handles communication with the PTZ server API |
| `ControlPanel` | Widget providing camera movement controls |
| `PositionDisplay` | Widget showing current camera position |
| `SafetyLimitIndicator` | Visual indicator for safety limit warnings |

## User Interface Visualization

### Window Layout

```
+--------------------------------------------------------------+
|  PTZ Camera Control (API Client)                     - □ X   |
+--------------------------------------------------------------+
|                                                              |
|  +----------------------------------------------------------+
|  |  Position                                               |
|  |                                                         |
|  |  Pan: 10.24°         Tilt: -5.67°                      |
|  |                                                         |
|  |  ■ Within safe range                                    |
|  +----------------------------------------------------------+
|                                                              |
|  +----------------------------------------------------------+
|  |  Controls                                               |
|  |                                                         |
|  |  Speed (1-63): [  16  ] ▲▼                              |
|  |                                                         |
|  |                 +------+                                |
|  |                 |  ▲   |                                |
|  |                 +------+                                |
|  |                                                         |
|  |  +------+      +------+      +------+                  |
|  |  |  ◄   |      |  ■   |      |  ►   |                  |
|  |  +------+      +------+      +------+                  |
|  |                                                         |
|  |                 +------+                                |
|  |                 |  ▼   |                                |
|  |                 +------+                                |
|  |                                                         |
|  |  [      Set Current Position as Home       ]            |
|  |                                                         |
|  |  Pan Angle:  [   0.00   ] ▲▼    Tilt Angle: [   0.00   ] ▲▼ |
|  |                                                         |
|  |  [         Go to Absolute Position         ]            |
|  |                                                         |
|  +----------------------------------------------------------+
|                                                              |
+--------------------------------------------------------------+
|  ● Connected                                                 |
+--------------------------------------------------------------+
```

### Component Description

#### Position Display Panel
The top panel shows the current camera position relative to the home position:
- Pan angle display (horizontal rotation)
- Tilt angle display (vertical angle)
- Safety limit indicator (changes color when approaching limits)

#### Controls Panel
The middle panel contains all user controls:

##### Movement Controls
- Speed selector: Controls the movement speed (1-63)
- Arrow buttons: Directional controls for camera movement (press and hold)
  - ▲: Tilt up (continuous movement while held)
  - ▼: Tilt down (continuous movement while held)
  - ◄: Pan left (continuous movement while held)
  - ►: Pan right (continuous movement while held)
- Stop button (■): Immediately halts all movement

##### Position Controls
- "Set Current Position as Home" button: Defines current position as the zero-reference point
- Absolute position controls:
  - Pan angle input: For precise horizontal positioning
  - Tilt angle input: For precise vertical positioning
  - "Go to Absolute Position" button: Moves camera to specified coordinates

#### Status Bar
The bottom bar shows:
- Connection status indicator:
  - ● Connected (green): Successfully connected to the PTZ server
  - ◯ Disconnected (red): Not connected to the PTZ server
- Temporary status messages (not shown in visualization)

### Interface States and Feedback

- Active movement buttons highlight in blue when pressed
- Safety indicator shows green when within safe range, orange when approaching limits
- Connection indicator shows green dot when connected, red circle when disconnected
- Error messages appear as popup dialogs
- Status messages appear temporarily in the status bar

## Module Files

### main_window_api.py

The `MainWindowAPI` class serves as the main application window and coordinates all other GUI components.

**Key Features:**
- Manages the overall application layout
- Coordinates communication between the control panel and API client
- Handles safety limit checking
- Provides movement control logic
- Manages connection status display

**Important Methods:**
- `__init__(api_url='http://localhost:5000')`: Initializes the main window with API server URL
- `handle_movement(direction, speed)`: Processes continuous movement requests from the control panel
- `stop_movement()`: Halts all camera movement
- `go_to_absolute_position(pan, tilt)`: Moves camera to specified absolute position
- `set_home_position()`: Sets current position as the home position
- `on_position_updated(rel_pan, rel_tilt, raw_pan, raw_tilt)`: Updates UI with new position data
- `check_safety_limits(direction, rel_pan, rel_tilt)`: Verifies movement safety based on position

### api_client.py

The `APIClient` class handles all communication with the PTZ server API, implementing both WebSocket (Socket.IO) and HTTP-based communication.

**Key Features:**
- WebSocket-based real-time updates via Socket.IO
- Automatic fallback to HTTP polling if WebSocket fails
- Threaded request handling to prevent UI blocking
- Connection status monitoring
- Error handling and reporting

**Important Methods:**
- `__init__(server_url='http://localhost:5000')`: Initializes the API client
- `move(direction, speed)`: Controls continuous camera movement in specified direction
- `stop()`: Immediately stops all camera movement (uses move with 'stop' direction)
- `get_position()`: Retrieves current camera position
- `set_home_position()`: Sets current position as the home position
- `set_absolute_position(pan, tilt)`: Moves to specified absolute position

**Signals:**
- `position_updated(rel_pan, rel_tilt, raw_pan, raw_tilt)`: Emitted when position data changes
- `connection_status_changed(connected)`: Emitted when connection status changes

### control_panel.py

The `ControlPanel` class provides a widget with camera movement controls and settings.

**Key Features:**
- Speed control for continuous movement (1-63)
- Directional buttons (up, down, left, right) with press-and-hold behavior
- Button release detection for automatic stopping
- Stop button for emergency halt
- Home position setting
- Absolute position movement controls

**Important Methods:**
- `__init__()`: Initializes the control panel components
- `go_to_absolute_position()`: Calls main window method to move to absolute position
- `on_direction_button_released()`: Handles button release to stop movement

**Signals:**
- `move_requested(direction, speed)`: Emitted when movement button is pressed/released
- `home_set_requested()`: Emitted when Set Home button is clicked

### position_display.py

The `PositionDisplay` class provides a widget that shows the current camera position.

**Key Features:**
- Displays pan and tilt angles relative to home position
- Includes safety limit indicator with color coding
- Updates in real-time with position changes

**Important Methods:**
- `__init__()`: Initializes the position display components
- `update_display(rel_pan, rel_tilt)`: Updates position labels with new values
- `set_limit_indicator(near_limit)`: Updates safety indicator based on proximity to limits

### safety_indicator.py

The `SafetyLimitIndicator` class implements a simple colored indicator for safety limits.

**Key Features:**
- Visual indicator that changes color based on safety status
- Green when within safe operating range
- Red when approaching or exceeding safety limits

**Important Methods:**
- `__init__()`: Initializes the indicator
- `set_near_limit(is_near_limit)`: Updates the indicator state
- `update_color()`: Changes indicator color based on current state

### app.py

The `app.py` file contains the legacy entry point for standalone GUI operation with direct controller connection.

**Key Features:**
- Command-line parameter handling for port, baudrate, and device address
- Controller initialization and error handling
- Application lifecycle management

> **Note:** This file is being phased out in favor of the API-based approach using `main_window_api.py`

### __init__.py

Standard Python package initialization file that makes the directory a proper Python package.

## Workflow and Data Flow

1. The `APIClient` establishes a connection to the PTZ server using WebSockets (Socket.IO)
2. User interacts with the `ControlPanel` by clicking direction buttons or entering absolute positions
3. Control signals are emitted to the `MainWindowAPI` which processes them
4. `MainWindowAPI` performs safety checks before sending commands to the `APIClient`
5. `APIClient` sends commands to the server via HTTP requests (in background threads)
6. Server processes commands and sends position updates via WebSocket
7. `APIClient` receives position updates and emits signals
8. `MainWindowAPI` receives signals and updates the `PositionDisplay`

## Safety Features

The GUI implements several safety features:

1. **Position Limits**: Prevents movement beyond configured safety limits
2. **Visual Indicators**: Color-coded indicators for proximity to safety limits
3. **Emergency Stop**: Dedicated stop button for immediate halt
4. **Limit Warnings**: Warning dialogs when attempting to exceed safety limits
5. **Step Size Limitation**: Prevents excessively large movement steps

## Implementation Notes

### Threading

The GUI makes extensive use of threading to ensure UI responsiveness:

- API requests are performed in background threads
- Socket.IO connection is managed asynchronously
- Position polling (fallback) runs in a dedicated thread

### Error Handling

The GUI implements robust error handling:

- Connection failures trigger automatic fallback to polling
- All API requests include timeout and error handling
- User-friendly error messages for common issues
- Last error tracking for debugging

### Real-time Updates

The GUI provides real-time position updates through:

1. Primary: WebSocket-based updates via Socket.IO
2. Fallback: HTTP polling if WebSockets fail

## Usage Examples

### Starting the GUI

```python
from PyQt5.QtWidgets import QApplication
import sys
from gui.main_window_api import MainWindowAPI

app = QApplication(sys.argv)
window = MainWindowAPI(api_url='http://localhost:8080')
window.show()
sys.exit(app.exec_())
```

### Custom Position Display

```python
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
import sys
from gui.position_display import PositionDisplay

app = QApplication(sys.argv)
window = QMainWindow()
layout = QVBoxLayout()
position_display = PositionDisplay()
layout.addWidget(position_display)

# Update with sample values
position_display.update_display(10.5, -5.2)
position_display.set_limit_indicator(False)  # Not near limits

container = QWidget()
container.setLayout(layout)
window.setCentralWidget(container)
window.show()
sys.exit(app.exec_())
```

## Extension Points

The GUI can be extended in several ways:

1. **Additional Controls**: Add new widgets to control additional camera features
2. **Enhanced Visualization**: Implement graphical position visualization
3. **Presets**: Add camera position presets for quick recall
4. **Statistics**: Add operational statistics and monitoring
5. **Keyboard Shortcuts**: Implement keyboard shortcuts for common operations

## Dependencies

- Python 3.6+
- PyQt5
- Socket.IO Client
- Requests
