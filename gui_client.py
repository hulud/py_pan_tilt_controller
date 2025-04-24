#!/usr/bin/env python3
"""
GUI Client Startup Script

This script starts the PTZ control GUI client that connects to the API server.
"""
import os
import sys
import argparse
import logging
from PyQt5.QtWidgets import QApplication
from src.utils import load_config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add parent directory to path to import gui package
# This is necessary because the GUI package hasn't been refactored yet
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gui.main_window_api import MainWindowAPI

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='PTZ Control GUI Client')
    parser.add_argument('--config', help='Path to configuration file')
    parser.add_argument('--server', help='API server URL (e.g., http://localhost:5000)')
    parser.add_argument('--host', help='API server host')
    parser.add_argument('--port', type=int, help='API server port')
    return parser.parse_args()

def main():
    """Main entry point"""
    # Parse command line arguments
    args = parse_args()
    
    # Load configuration
    try:
        config = load_config(args.config)
        client_config = config.get('client', {})
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        client_config = {}
    
    # Determine server URL
    server_url = args.server
    if not server_url:
        host = args.host or client_config.get('host', 'localhost')
        port = args.port or client_config.get('port', 5000)
        server_url = f"http://{host}:{port}"
    
    # Create Qt application
    app = QApplication(sys.argv)
    app.setApplicationName("PTZ Control")
    
    # Create main window
    main_window = MainWindowAPI(api_url=server_url)
    main_window.show()
    
    # Run application
    try:
        return app.exec_()
    except Exception as e:
        logger.error(f"Error running application: {e}")
        return 1

if __name__ == '__main__':
    import sys
    sys.exit(main())
