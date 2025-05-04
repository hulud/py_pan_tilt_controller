# Utils Module Documentation

The `utils` module provides utility functions for the PTZ camera control system, primarily focused on configuration management.

## Module Overview

The utils module contains functions for:
- Loading configuration from YAML files
- Extracting specific configuration sections for different system components

## File Structure

```
utils/
├── __init__.py     # Exports the module's public interface
├── config.py       # Configuration management functions
└── documentation.md  # This documentation file
```

## Functions Reference

### Configuration Management (`config.py`)

#### `load_config(config_path: Optional[str] = None) -> Dict[str, Any]`

Loads configuration from a YAML file.

**Parameters:**
- `config_path` (Optional[str]): Path to the configuration file. If None, the function will search for the configuration file in standard locations:
  - `<project_root>/config/settings.yaml`
  - `<project_root>/config.yaml`
  - `<current_working_directory>/config/settings.yaml`
  - `<current_working_directory>/config.yaml`

**Returns:**
- Dictionary containing the loaded configuration.

**Raises:**
- `FileNotFoundError`: If the configuration file cannot be found.
- `yaml.YAMLError`: If the configuration file is not valid YAML.

**Example Usage:**
```python
from src.utils import load_config

# Load configuration from default location
config = load_config()

# Load configuration from specific path
config = load_config('/path/to/custom/config.yaml')
```

#### `get_connection_config(config: Dict[str, Any]) -> Dict[str, Any]`

Extracts the connection-specific configuration from the full configuration dictionary.

**Parameters:**
- `config` (Dict[str, Any]): The complete configuration dictionary.

**Returns:**
- Dictionary containing the 'connection' section of the configuration.

**Example Usage:**
```python
from src.utils import load_config, get_connection_config

config = load_config()
conn_config = get_connection_config(config)

# Access connection parameters
port = conn_config.get('port', 'COM1')
baudrate = conn_config.get('baudrate', 9600)
```

#### `get_controller_config(config: Dict[str, Any]) -> Dict[str, Any]`

Extracts the controller-specific configuration from the full configuration dictionary.

**Parameters:**
- `config` (Dict[str, Any]): The complete configuration dictionary.

**Returns:**
- Dictionary containing the 'controller' section of the configuration.

**Example Usage:**
```python
from src.utils import load_config, get_controller_config

config = load_config()
ctrl_config = get_controller_config(config)

# Access controller parameters
address = ctrl_config.get('address', 1)
protocol = ctrl_config.get('protocol', 'pelco_d')
```

#### `get_api_config(config: Dict[str, Any]) -> Dict[str, Any]`

Extracts the API-specific configuration from the full configuration dictionary.

**Parameters:**
- `config` (Dict[str, Any]): The complete configuration dictionary.

**Returns:**
- Dictionary containing the 'api' section of the configuration.

**Example Usage:**
```python
from src.utils import load_config, get_api_config

config = load_config()
api_config = get_api_config(config)

# Access API parameters
host = api_config.get('host', '127.0.0.1')
port = api_config.get('port', 5000)
debug = api_config.get('debug', False)
```

## Configuration File Structure

The utility functions expect a YAML configuration file with the following structure:

```yaml
connection:
  port: COM3            # Serial port for PTZ camera
  baudrate: 9600
  timeout: 1.0
  retries: 3
  retry_delay: 0.5
  polling_rate: 0.5
  enable_polling: true

controller:
  address: 1
  protocol: pelco_d
  default_speed: 25
  timeout: 1.0

api:
  host: 127.0.0.1
  port: 8080
  debug: false

# Additional sections can be included but are not processed by these utilities
```

## Best Practices

- Always use the utility functions rather than directly accessing the configuration to ensure consistent behavior across the application.
- Handle exceptions from `load_config()` to provide meaningful error messages to users.
- Use default values when accessing configuration parameters to handle missing values gracefully:
  ```python
  timeout = conn_config.get('timeout', 1.0)  # Default 1.0 second timeout
  ```

## Integration with Other Modules

These utility functions are typically used at the application startup to load configuration:

1. In `ptz_server.py`, to configure the server, controller, and connection components
2. In `gui_client.py`, to configure the client and its connection to the server
3. In `run_all.py`, to configure both server and client components when running the complete system
