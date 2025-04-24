#!/usr/bin/env python3
"""
Combined Startup Script

This script starts both the PTZ control server and GUI client.
"""
import os
import sys
import argparse
import logging
import threading
import time
import subprocess

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='PTZ Control System')
    parser.add_argument('--config', help='Path to configuration file')
    parser.add_argument('--host', help='Host address to listen on')
    parser.add_argument('--port', type=int, help='Port to listen on')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    return parser.parse_args()

def server_thread(args):
    """Function to run the server in a separate thread"""
    cmd = [sys.executable, 'ptz_server.py']
    
    if args.config:
        cmd.extend(['--config', args.config])
    if args.host:
        cmd.extend(['--host', args.host])
    if args.port:
        cmd.extend(['--port', str(args.port)])
    if args.debug:
        cmd.append('--debug')
    
    logger.info(f"Starting server with command: {' '.join(cmd)}")
    
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        
        # Log server output
        for line in process.stdout:
            line = line.strip()
            if line:
                logger.info(f"Server: {line}")
    except Exception as e:
        logger.error(f"Error running server: {e}")
    finally:
        if process:
            process.terminate()

def client_thread(args):
    """Function to run the GUI client in a separate thread"""
    # Wait for server to start
    time.sleep(2)
    
    cmd = [sys.executable, 'gui_client.py']
    
    if args.config:
        cmd.extend(['--config', args.config])
    if args.host:
        cmd.extend(['--host', args.host])
    if args.port:
        cmd.extend(['--port', str(args.port)])
    
    logger.info(f"Starting client with command: {' '.join(cmd)}")
    
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        
        # Log client output
        for line in process.stdout:
            line = line.strip()
            if line:
                logger.info(f"Client: {line}")
    except Exception as e:
        logger.error(f"Error running client: {e}")
    finally:
        if process:
            process.terminate()

def main():
    """Main entry point"""
    # Parse command line arguments
    args = parse_args()
    
    # Start server in a separate thread
    server_thread_obj = threading.Thread(target=server_thread, args=(args,), daemon=True)
    server_thread_obj.start()
    
    # Start client in a separate thread
    client_thread_obj = threading.Thread(target=client_thread, args=(args,), daemon=True)
    client_thread_obj.start()
    
    # Wait for threads to complete
    try:
        while True:
            if not client_thread_obj.is_alive():
                logger.info("Client thread exited, stopping application")
                break
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Application stopped by user")
    
    return 0

if __name__ == '__main__':
    import sys
    sys.exit(main())
