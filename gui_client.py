#!/usr/bin/env python3
"""
GUI Client Startup Script

This script starts the PTZ control GUI client that connects to the API server
using settings from the YAML configuration file.
"""
import os
import sys
import logging
from PyQt5.QtWidgets import QApplication

from gui.main_window_api import MainWindowAPI
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

def main():
    """Main entry point"""
    # Load configuration
    try:
        config = load_config()
        client_config = config.get('client', {})
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        client_config = {}

    # Determine server URL
    host = client_config.get('host', 'localhost')
    port = client_config.get('port', 8080)
    server_url = f"http://{host}:{port}"

    logger.info(f"Connecting to PTZ API server at {server_url}")

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
