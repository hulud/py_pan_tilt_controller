#!/usr/bin/env python3
"""
Pan Tilt GUI Launcher with API Client

Launches the GUI application with the API client interface.
"""

import sys
import os
import yaml
import argparse
from PyQt5.QtWidgets import QApplication
from gui.main_window_api import MainWindowAPI

def load_config():
    """Load configuration from YAML file"""
    config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading config: {e}")
        return {
            'server': {
                'host': 'localhost',
                'port': 5000
            }
        }

def main():
    """Main entry point for the GUI application"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Pan Tilt Camera Control GUI (API Client)")
    parser.add_argument("--server", help="API server URL", default=None)
    parser.add_argument("--host", help="API server host", default=None)
    parser.add_argument("--port", help="API server port", type=int, default=None)
    args = parser.parse_args()
    
    # Load configuration
    config = load_config()
    
    # Determine API server URL
    if args.server:
        api_url = args.server
    else:
        # Always use localhost for client connections, never 0.0.0.0
        host = args.host or config.get('client', {}).get('host', 'localhost')
        # If host is 0.0.0.0, replace with localhost for client connection
        if host == "0.0.0.0":
            host = "localhost"  
            
        port = args.port or config.get('server', {}).get('port', 5000)
        api_url = f"http://{host}:{port}"
    
    print(f"Connecting to API server at {api_url}")
    
    # Create Qt application
    app = QApplication(sys.argv)
    
    # Create main window
    window = MainWindowAPI(api_url=api_url)
    window.show()
    
    # Run event loop
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
