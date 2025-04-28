#!/usr/bin/env python3
"""
GUI client entry point: launches the Qt MainWindow-based PTZ controller.
This version uses MainWindow only, dropping any WebView/HTML UI.
"""
import sys
import argparse

from PyQt5.QtWidgets import QApplication, QMessageBox

# Import your MainWindow class from the Qt GUI module
from gui.main_window import MainWindow
# Import your REST API client
from src.api.client import APIClient


def parse_args():
    parser = argparse.ArgumentParser(
        description="PTZ Controller GUI Client (Qt MainWindow only)"
    )
    parser.add_argument(
        "--server", "-s",
        default="http://127.0.0.1:8080",
        help="Base URL of the PTZ API server (e.g. http://127.0.0.1:8080)"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # Initialize Qt application
    app = QApplication(sys.argv)

    # Initialize API client
    try:
        api_client = APIClient(base_url=args.server)
    except Exception as err:
        QMessageBox.critical(
            None,
            "Initialization Error",
            f"Could not create API client: {err}"
        )
        sys.exit(1)

    # Create and show the main window
    window = MainWindow(api_client)
    window.show()

    # Start the Qt event loop
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
