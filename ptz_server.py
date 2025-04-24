#!/usr/bin/env python3
"""
PTZ Server Startup Script

This script starts the PTZ control server with the API endpoints.
"""
import os
import argparse
import logging
from src.utils import load_config, get_connection_config, get_controller_config, get_api_config
from src.controller import PTZController
from src.api import create_app, register_routes

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='PTZ Control Server')
    parser.add_argument('--config', help='Path to configuration file')
    parser.add_argument('--host', help='Host address to listen on')
    parser.add_argument('--port', type=int, help='Port to listen on')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    return parser.parse_args()

def main():
    """Main entry point"""
    # Parse command line arguments
    args = parse_args()
    
    # Load configuration
    try:
        config = load_config(args.config)
        connection_config = get_connection_config(config)
        controller_config = get_controller_config(config)
        api_config = get_api_config(config)
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        return 1
    
    # Override config with command line arguments
    if args.host:
        api_config['host'] = args.host
    if args.port:
        api_config['port'] = args.port
    if args.debug:
        api_config['debug'] = True
    
    # Create controller
    try:
        controller = PTZController(
            connection_config=connection_config,
            address=controller_config.get('address', 1)
        )
    except Exception as e:
        logger.error(f"Error creating controller: {e}")
        return 1
    
    # Create API server
    app, socketio = create_app(api_config)
    register_routes(app, socketio, controller)
    
    # Run server
    try:
        host = api_config.get('host', '127.0.0.1')
        port = api_config.get('port', 5000)
        debug = api_config.get('debug', False)
        
        logger.info(f"Starting PTZ Control Server on {host}:{port}")
        socketio.run(
            app,
            host=host,
            port=port,
            debug=debug,
            allow_unsafe_werkzeug=True
        )
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Error running server: {e}")
        return 1
    finally:
        # Clean up resources
        controller.close()
    
    return 0

if __name__ == '__main__':
    import sys
    sys.exit(main())
