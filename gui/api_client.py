#!/usr/bin/env python3
"""
API Client for Pan-Tilt Camera Control

Handles communication with the API server for the GUI.
"""

import requests
import json
import threading
import time
import logging
import socketio
from PyQt5.QtCore import QObject, pyqtSignal, QThread

logger = logging.getLogger(__name__)

# Set shorter default timeouts
DEFAULT_REQUEST_TIMEOUT = 0.5  # 500ms timeout for HTTP requests

class APIClient(QObject):
    """
    Client for communicating with the Pan-Tilt API Server
    """
    
    # Define signals for notifications from server
    position_updated = pyqtSignal(float, float, float, float)
    connection_status_changed = pyqtSignal(bool)
    
    def __init__(self, server_url='http://localhost:5000'):
        """
        Initialize the API client
        
        Args:
            server_url: Base URL of the API server
        """
        super().__init__()
        
        self.server_url = server_url
        self.connected = False
        self.last_error = None
        
        # Setup Socket.IO for real-time updates
        self.sio = socketio.Client(reconnection=True, reconnection_attempts=5, 
                                  reconnection_delay=1, reconnection_delay_max=5)
        self.setup_socketio()
        
        # Setup polling as fallback mechanism
        self.polling = False
        self.polling_thread = None
        
        # Create a session for connection pooling
        self.session = requests.Session()
        
        # Try initial connection in background thread to prevent GUI blocking
        threading.Thread(target=self._connect, daemon=True).start()
    
    def setup_socketio(self):
        """Set up Socket.IO event handlers"""
        
        @self.sio.event
        def connect():
            logger.info("Connected to API server")
            self.connected = True
            self.connection_status_changed.emit(True)
            # Request position update immediately
            self.sio.emit('request_position')
            
            # Stop polling if it was active
            if self.polling:
                self.stop_polling()
        
        @self.sio.event
        def disconnect():
            logger.info("Disconnected from API server")
            self.connected = False
            self.connection_status_changed.emit(False)
            
            # Start polling as fallback
            if not self.polling:
                self.start_polling()
        
        @self.sio.event
        def position_update(data):
            rel_pan = data.get('rel_pan')
            rel_tilt = data.get('rel_tilt')
            raw_pan = data.get('raw_pan')
            raw_tilt = data.get('raw_tilt')
            if rel_pan is not None and rel_tilt is not None and raw_pan is not None and raw_tilt is not None:
                self.position_updated.emit(rel_pan, rel_tilt, raw_pan, raw_tilt)
        
        @self.sio.event
        def error(data):
            logger.error(f"Socket.IO error: {data.get('message')}")
            self.last_error = data.get('message')
    
    def _connect(self):
        """Connect to the API server"""
        try:
            # Connect with short timeout to avoid blocking
            self.sio.connect(self.server_url, wait=False)
        except Exception as e:
            logger.error(f"Failed to connect to API server: {e}")
            self.connected = False
            self.connection_status_changed.emit(False)
            self.last_error = str(e)
            # Start polling as fallback
            self.start_polling()
    
    def start_polling(self):
        """Start polling for position updates as fallback"""
        if not self.polling:
            self.polling = True
            self.polling_thread = threading.Thread(target=self._polling_loop, daemon=True)
            self.polling_thread.start()
            logger.info("Started polling for position updates")
    
    def stop_polling(self):
        """Stop the polling thread"""
        self.polling = False
        if self.polling_thread:
            self.polling_thread.join(timeout=1)
            self.polling_thread = None
            logger.info("Stopped polling for position updates")
    
    def _polling_loop(self):
        """Polling loop for position updates"""
        while self.polling:
            try:
                response = self.session.get(
                    f"{self.server_url}/api/device/position",
                    timeout=DEFAULT_REQUEST_TIMEOUT
                )
                if response.status_code == 200:
                    data = response.json()
                    rel_pan = data.get('rel_pan')
                    rel_tilt = data.get('rel_tilt')
                    raw_pan = data.get('raw_pan')
                    raw_tilt = data.get('raw_tilt')
                    if rel_pan is not None and rel_tilt is not None and raw_pan is not None and raw_tilt is not None:
                        self.position_updated.emit(rel_pan, rel_tilt, raw_pan, raw_tilt)
                    
                    # If we got a successful response but weren't connected, try to reconnect
                    if not self.connected:
                        threading.Thread(target=self._connect, daemon=True).start()
            except Exception as e:
                logger.error(f"Error in polling loop: {e}")
                self.last_error = str(e)
            
            time.sleep(0.2)  # Poll every 200ms
    
    def close(self):
        """Close the connection and clean up resources"""
        self.stop_polling()
        try:
            self.sio.disconnect()
        except Exception as e:
            logger.error(f"Error disconnecting from server: {e}")
        
        # Close the session
        self.session.close()
    
    # API Methods
    
    def move(self, direction, speed=0x10):
        """
        Start movement in a specific direction
        
        Args:
            direction: One of 'up', 'down', 'left', 'right'
            speed: Movement speed (0x00-0x3F)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Use background thread for movement requests to prevent UI lag
            threading.Thread(
                target=self._send_move_request,
                args=(direction, speed),
                daemon=True
            ).start()
            return True  # Return immediately for responsive UI
        except Exception as e:
            self.last_error = str(e)
            logger.error(f"Movement thread error: {e}")
            return False
    
    def _send_move_request(self, direction, speed):
        """Send the actual movement request in a background thread"""
        try:
            self.session.post(
                f"{self.server_url}/api/device/movement/{direction}",
                json={'speed': speed},
                headers={'Content-Type': 'application/json'},
                timeout=DEFAULT_REQUEST_TIMEOUT
            )
        except Exception as e:
            self.last_error = str(e)
            logger.error(f"Movement request error: {e}")
    
    def stop(self):
        """
        Stop all movement
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Stop requests should be prioritized and sent immediately
            response = self.session.post(
                f"{self.server_url}/api/device/movement/stop",
                timeout=DEFAULT_REQUEST_TIMEOUT
            )
            
            if response.status_code == 200:
                return True
            else:
                data = response.json()
                self.last_error = data.get('message', 'Unknown error')
                logger.error(f"Stop error: {self.last_error}")
                return False
        except Exception as e:
            self.last_error = str(e)
            logger.error(f"Stop request error: {e}")
            return False
    
    def get_position(self):
        """
        Get current position
        
        Returns:
            Tuple of (rel_pan, rel_tilt, raw_pan, raw_tilt) or None on error
        """
        try:
            response = self.session.get(
                f"{self.server_url}/api/device/position",
                timeout=DEFAULT_REQUEST_TIMEOUT
            )
            
            if response.status_code == 200:
                data = response.json()
                rel_pan = data.get('rel_pan')
                rel_tilt = data.get('rel_tilt')
                raw_pan = data.get('raw_pan')
                raw_tilt = data.get('raw_tilt')
                return (rel_pan, rel_tilt, raw_pan, raw_tilt)
            else:
                data = response.json()
                self.last_error = data.get('message', 'Unknown error')
                logger.error(f"Position query error: {self.last_error}")
                return None
        except Exception as e:
            self.last_error = str(e)
            logger.error(f"Position request error: {e}")
            return None
    
    def set_home_position(self):
        """
        Set current position as home
        
        Returns:
            True if successful, False otherwise
        """
        try:
            response = self.session.post(
                f"{self.server_url}/api/device/home",
                timeout=DEFAULT_REQUEST_TIMEOUT
            )
            
            if response.status_code == 200:
                return True
            else:
                data = response.json()
                self.last_error = data.get('message', 'Unknown error')
                logger.error(f"Set home error: {self.last_error}")
                return False
        except Exception as e:
            self.last_error = str(e)
            logger.error(f"Set home request error: {e}")
            return False
    
    def set_absolute_position(self, pan=None, tilt=None, step_size=None):
        """
        Move to absolute position
        
        Args:
            pan: Pan angle in degrees (0-360) or None to skip
            tilt: Tilt angle in degrees (-90 to +90) or None to skip
            step_size: Size of step in degrees (optional)
            
        Returns:
            True if successful, False otherwise
        """
        data = {}
        if pan is not None:
            data['pan'] = pan
        if tilt is not None:
            data['tilt'] = tilt
        if step_size is not None:
            data['step_size'] = step_size
        
        try:
            # Handle absolute position requests in a background thread
            threading.Thread(
                target=self._send_absolute_position_request,
                args=(data,),
                daemon=True
            ).start()
            return True
        except Exception as e:
            self.last_error = str(e)
            logger.error(f"Absolute position thread error: {e}")
            return False
    
    def _send_absolute_position_request(self, data):
        """Send absolute position request in background thread"""
        try:
            self.session.post(
                f"{self.server_url}/api/device/position/absolute",
                json=data,
                headers={'Content-Type': 'application/json'},
                timeout=DEFAULT_REQUEST_TIMEOUT
            )
        except Exception as e:
            self.last_error = str(e)
            logger.error(f"Absolute position request error: {e}")
