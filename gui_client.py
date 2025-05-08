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
    
    # Set application-wide scaling if needed (for high DPI screens)
    # Check if any command line arguments include scaling options
    scaling_factor = None
    for arg in sys.argv:
        if arg.startswith('--scale='):
            try:
                scaling_factor = float(arg.split('=')[1])
                logger.info(f"Using command line scaling factor: {scaling_factor}")
            except (IndexError, ValueError):
                logger.warning(f"Invalid scaling factor: {arg}")
    
    if scaling_factor:
        # Apply high DPI scaling
        app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
        # Set custom scale factor if specified
        from PyQt5.QtCore import Qt, QCoreApplication
        QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        QCoreApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

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
