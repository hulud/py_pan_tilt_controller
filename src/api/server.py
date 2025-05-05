"""
API server implementation.

This module provides the Flask application factory and basic setup
for the REST API server.
"""
import os
import yaml
import logging
from typing import Dict, Any, Optional
from flask import Flask
from flask_socketio import SocketIO
from flask_cors import CORS

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_app(config: Optional[Dict[str, Any]] = None, socketio_mode: str = 'threading') -> tuple:
    """
    Create and configure Flask application.
    
    Args:
        config: API configuration or None to load from file
        socketio_mode: SocketIO async mode ('threading', 'eventlet', 'gevent')
        
    Returns:
        Tuple of (app, socketio) objects
    """
    # Create Flask app
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'pan-tilt-api-secret'
    
    # Enable CORS
    CORS(app)
    
    # Create SocketIO instance
    socketio = SocketIO(
        app, 
        cors_allowed_origins="*", 
        async_mode=socketio_mode,
        # Add explicit path and improve logging for debugging
        path='socket.io',
        logger=True,
        engineio_logger=False
    )
    
    # Apply configuration
    if config is None:
        config = {}
    
    app.config.update(config)
    
    return app, socketio


def run_app(app: Flask, 
           socketio: SocketIO, 
           host: str = '127.0.0.1', 
           port: int = 5000, 
           debug: bool = False,
           use_reloader: bool = False):
    """
    Run the Flask application with SocketIO support.
    
    Args:
        app: Flask application instance
        socketio: SocketIO instance
        host: Host address to listen on
        port: Port to listen on
        debug: Enable debug mode
        use_reloader: Enable auto-reloading
    """
    logger.info(f"Starting PTZ Control API Server on {host}:{port}")
    
    socketio.run(app, 
                host=host,
                port=port, 
                debug=debug, 
                use_reloader=use_reloader,
                allow_unsafe_werkzeug=True)
