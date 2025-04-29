#!/usr/bin/env python3
"""
Combined Startup Script

This script starts both the PTZ control server and GUI client using
configuration from the YAML file (no command-line arguments).
"""
import logging
import threading
import time
import subprocess
import sys
import os
import signal
import atexit
import yaml
import re
import pathlib

# Load configuration from YAML
def load_config():
    config_path = pathlib.Path('config/settings.yaml')
    if not config_path.exists():
        print(f"Warning: Configuration file {config_path} not found. Using defaults.")
        return {}
    
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

# Setup logging based on YAML configuration
def setup_logging(config):
    log_config = config.get('logging', {})
    
    # Create base logger with default formatter
    logging.basicConfig(
        level=getattr(logging, log_config.get('root_level', 'INFO')),
        format='%(asctime)s.%(msecs)03d - %(name)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Create log directory if needed
    log_dir = log_config.get('log_dir', 'logs')
    if log_config.get('file_output', True) and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    
    # Configure loggers based on config
    configured_loggers = {}
    logger_configs = log_config.get('loggers', {})
    
    # Initialize all loggers with their specific levels
    for logger_name, level in logger_configs.items():
        logger = logging.getLogger(logger_name)
        logger.setLevel(getattr(logging, level, logging.INFO))
        configured_loggers[logger_name] = logger
        
        # Add file handler if enabled
        if log_config.get('file_output', True):
            file_handler = logging.FileHandler(os.path.join(log_dir, f"{logger_name}.log"))
            file_handler.setFormatter(logging.Formatter('%(asctime)s.%(msecs)03d - %(name)s - %(levelname)s - %(message)s', datefmt='%H:%M:%S'))
            logger.addHandler(file_handler)
    
    # Compile pattern matchers for unconfigured loggers
    pattern_rules = []
    for pattern, level in log_config.get('patterns', {'*': 'INFO'}).items():
        if '*' in pattern:
            regex_pattern = pattern.replace('.', '\\.').replace('*', '.*')
            pattern_rules.append((re.compile(f"^{regex_pattern}$"), getattr(logging, level, logging.INFO)))
    
    # Return all configuration
    return configured_loggers, pattern_rules

# Load configuration and setup logging
config = load_config()
configured_loggers, pattern_rules = setup_logging(config)

# Get or create loggers with appropriate levels
def get_logger(name):
    # If already configured, return it
    if name in configured_loggers:
        return configured_loggers[name]
    
    # Create new logger
    logger = logging.getLogger(name)
    
    # Apply pattern rules
    for pattern, level in pattern_rules:
        if pattern.match(name):
            logger.setLevel(level)
            break
    
    # Store for future use
    configured_loggers[name] = logger
    return logger

# Get main loggers we'll use
logger = get_logger('run_all')
server_logger = get_logger('run_all.server_thread')
serial_tx_logger = get_logger('run_all.server_thread.serial_tx')
serial_rx_logger = get_logger('run_all.server_thread.serial_rx')
zero_point_logger = get_logger('run_all.server_thread.zero_point')
parser_logger = get_logger('run_all.server_thread.parser')
client_logger = get_logger('run_all.client_thread')

# Global process references for clean shutdown
server_process = None
client_process = None

def terminate_processes():
    """Clean up function to terminate all processes"""
    global server_process, client_process
    
    logger.info("Cleaning up processes...")
    
    # Terminate client process
    if client_process and client_process.poll() is None:
        logger.info("Terminating client process...")
        try:
            if sys.platform == 'win32':
                # Windows termination
                client_process.terminate()
            else:
                # Unix termination
                os.killpg(os.getpgid(client_process.pid), signal.SIGTERM)
            client_process.wait(timeout=3)
        except Exception as e:
            logger.error(f"Error terminating client process: {e}")
            # Force kill if termination failed
            try:
                if client_process.poll() is None:
                    if sys.platform == 'win32':
                        subprocess.call(['taskkill', '/F', '/T', '/PID', str(client_process.pid)])
                    else:
                        os.killpg(os.getpgid(client_process.pid), signal.SIGKILL)
            except Exception as e2:
                logger.error(f"Error force killing client process: {e2}")
    
    # Wait briefly before terminating server to allow proper socket disconnection
    time.sleep(0.5)
    
    # Terminate server process
    if server_process and server_process.poll() is None:
        logger.info("Terminating server process...")
        try:
            if sys.platform == 'win32':
                # Windows termination
                server_process.terminate()
            else:
                # Unix termination
                os.killpg(os.getpgid(server_process.pid), signal.SIGTERM)
            server_process.wait(timeout=3)
        except Exception as e:
            logger.error(f"Error terminating server process: {e}")
            # Force kill if termination failed
            try:
                if server_process.poll() is None:
                    if sys.platform == 'win32':
                        subprocess.call(['taskkill', '/F', '/T', '/PID', str(server_process.pid)])
                    else:
                        os.killpg(os.getpgid(server_process.pid), signal.SIGKILL)
            except Exception as e2:
                logger.error(f"Error force killing server process: {e2}")

def process_server_output(line):
    """Process and route server output to appropriate loggers"""
    line = line.strip()
    if not line:
        return
        
    # Route based on content patterns
    if "[SERIAL TX]" in line:
        serial_tx_logger.debug(f"Server: {line}")
    elif "[SERIAL RX]" in line:
        serial_rx_logger.debug(f"Server: {line}")
    elif "zero-point" in line.lower() or "zeroing" in line.lower():
        zero_point_logger.info(f"Server: {line}")
    elif "checksum mismatch" in line.lower() or "invalid response" in line.lower():
        parser_logger.warning(f"Server: {line}")
    else:
        # Default server logger
        server_logger.info(f"Server: {line}")

def server_thread():
    """Function to run the server in a separate thread"""
    global server_process
    cmd = [sys.executable, 'ptz_server.py']
    
    server_logger.info(f"Starting server with command: {' '.join(cmd)}")
    
    try:
        # Create a new process group on Unix systems
        kwargs = {}
        if sys.platform != 'win32':
            kwargs['preexec_fn'] = os.setsid
        
        server_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1,  # Line buffered output
            **kwargs
        )
        
        # Log server output with routing
        for line in server_process.stdout:
            process_server_output(line)
                
        # Check if process terminated with an error
        return_code = server_process.wait()
        if return_code != 0:
            server_logger.error(f"Server process exited with code {return_code}")
            return False
        return True
        
    except Exception as e:
        server_logger.error(f"Error running server: {e}")
        return False

def client_thread(server_ready_event):
    """Function to run the GUI client in a separate thread"""
    global client_process
    
    # Wait for server ready event
    if not server_ready_event.wait(timeout=10.0):
        client_logger.error("Timed out waiting for server to start")
        return False
    
    cmd = [sys.executable, 'gui_client.py']
    
    client_logger.info(f"Starting client with command: {' '.join(cmd)}")
    
    try:
        # Create a new process group on Unix systems
        kwargs = {}
        if sys.platform != 'win32':
            kwargs['preexec_fn'] = os.setsid
        
        client_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1,  # Line buffered output
            **kwargs
        )
        
        # Log client output
        for line in client_process.stdout:
            line = line.strip()
            if line:
                # Check if line appears to be API client related
                if "api_client" in line.lower() or "request" in line.lower() or "response" in line.lower():
                    gui_api_logger = logging.getLogger('gui_client.api_client')
                    gui_api_logger.info(f"Client: {line}")
                else:
                    client_logger.info(f"Client: {line}")
        
        # Check if process terminated with an error
        return_code = client_process.wait()
        if return_code != 0:
            client_logger.error(f"Client process exited with code {return_code}")
        return True
    
    except Exception as e:
        client_logger.error(f"Error running client: {e}")
        return False

def main():
    """Main entry point"""
    # Register cleanup handler
    atexit.register(terminate_processes)
    
    # Add signal handlers
    for sig in [signal.SIGINT, signal.SIGTERM]:
        signal.signal(sig, lambda s, f: (terminate_processes(), sys.exit(0)))
    
    logger.info("Starting Pan-Tilt Control System")
    
    # Event to signal when server is ready
    server_ready_event = threading.Event()
    
    # Start server in a separate thread
    server_thread_obj = threading.Thread(
        target=lambda: server_thread() and server_ready_event.set(),
        daemon=True
    )
    server_thread_obj.start()
    
    # Wait for server to initialize (at least partially)
    time.sleep(2)
    
    # Check if server started successfully by checking if it's still running
    if server_process is None or server_process.poll() is not None:
        logger.error("Server failed to start")
        terminate_processes()
        return 1
    
    server_ready_event.set()  # Signal that client can start
    
    # Start client in a separate thread
    client_thread_obj = threading.Thread(
        target=lambda: client_thread(server_ready_event),
        daemon=True
    )
    client_thread_obj.start()
    
    # Wait for threads to complete
    try:
        # Keep running until client exits or keyboard interrupt
        while True:
            if not client_thread_obj.is_alive() or (client_process and client_process.poll() is not None):
                logger.info("Client thread exited, stopping application")
                break
            if not server_thread_obj.is_alive() or (server_process and server_process.poll() is not None):
                logger.info("Server thread exited, stopping application")
                break
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Application stopped by user")
    finally:
        # Make sure processes are terminated
        terminate_processes()
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
