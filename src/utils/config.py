"""
Utilities for loading and managing configuration.
"""
import os
import yaml
from typing import Dict, Any, Optional


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load configuration from YAML file.
    
    Args:
        config_path: Path to configuration file. If None, looks in 'config/settings.yaml'
        
    Returns:
        Dictionary containing configuration
        
    Raises:
        FileNotFoundError: If config file not found
        yaml.YAMLError: If config file is not valid YAML
    """
    if config_path is None:
        # Try standard locations
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        possible_paths = [
            os.path.join(project_root, 'config', 'settings.yaml'),
            os.path.join(project_root, 'config.yaml'),
            # Also check in the current working directory
            os.path.join(os.getcwd(), 'config', 'settings.yaml'),
            os.path.join(os.getcwd(), 'config.yaml'),
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                config_path = path
                break
        
        if config_path is None:
            raise FileNotFoundError(f"Configuration file not found in {possible_paths}")
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    return config


def get_connection_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract connection configuration from loaded config.
    
    Args:
        config: Full configuration dictionary
        
    Returns:
        Connection configuration section
    """
    return config.get('connection', {})


def get_controller_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract controller configuration from loaded config.
    
    Args:
        config: Full configuration dictionary
        
    Returns:
        Controller configuration section
    """
    return config.get('controller', {})


def get_api_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract API configuration from loaded config.
    
    Args:
        config: Full configuration dictionary
        
    Returns:
        API configuration section
    """
    return config.get('api', {})
