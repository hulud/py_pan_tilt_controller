#!/usr/bin/env python3
"""
Pan-Tilt API Server

This server provides a REST API for controlling pan-tilt devices.
"""

import os
import yaml
import json
import time
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import threading
import logging
from werkzeug.serving import run_simple

# Import the Pelco controller
from pelco_D import PelcoDController

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app with async mode
app = Flask(__name__)
app.config['SECRET_KEY'] = 'pan-tilt-api-secret'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Load configuration
def load_config():
    config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        return {
            'device': {
                'port': None,
                'baudrate': 9600,
                'address': 1
            },
            'server': {
                'host': '127.0.0.1',
                'port': 5000
            }
        }

config = load_config()

# Initialize device controller
def create_device():
    device_config = config.get('device', {})
    
    try:
        return PelcoDController(
            port=device_config.get('port', 'COM3'),
            baudrate=device_config.get('baudrate', 9600),
            address=device_config.get('address', 1),
            blocking=device_config.get('blocking', False),
            timeout=device_config.get('timeout', 1.0)
        )
    except Exception as e:
        logger.error(f"Error creating device: {e}")
        raise

device = create_device()
logger.info(f"Device initialized on port {config.get('device', {}).get('port')}")

# Command queue for processing commands in order
command_queue = []
queue_lock = threading.Lock()
queue_processing = False

def process_command_queue():
    """Process queued commands to avoid overlapping operations"""
    global queue_processing
    
    with queue_lock:
        if queue_processing or not command_queue:
            return
        queue_processing = True
        cmd_func, args, kwargs, callback = command_queue.pop(0)
    
    try:
        result = cmd_func(*args, **kwargs)
        if callback:
            callback(result)
    except Exception as e:
        logger.error(f"Error processing command: {e}")
    finally:
        with queue_lock:
            queue_processing = False
            # Schedule next command processing if queue not empty
            if command_queue:
                threading.Thread(target=process_command_queue, daemon=True).start()

def queue_command(cmd_func, *args, callback=None, **kwargs):
    """Add command to queue and process in order"""
    with queue_lock:
        command_queue.append((cmd_func, args, kwargs, callback))
        if not queue_processing:
            threading.Thread(target=process_command_queue, daemon=True).start()

# Position update thread
def position_update_thread():
    """Thread that periodically emits position updates via WebSocket"""
    while True:
        try:
            rel_pan, rel_tilt, raw_pan, raw_tilt = device.get_relative_position()
            
            # No safety check needed
            if rel_pan is not None and rel_tilt is not None:
                socketio.emit('position_update', {
                    'rel_pan': rel_pan,
                    'rel_tilt': rel_tilt,
                    'raw_pan': raw_pan,
                    'raw_tilt': raw_tilt,
                    'timestamp': time.time(),
                    'safety_issue': False
                })
            else:
                socketio.emit('position_update', {
                    'rel_pan': rel_pan,
                    'rel_tilt': rel_tilt,
                    'raw_pan': raw_pan,
                    'raw_tilt': raw_tilt,
                    'timestamp': time.time()
                })
        except Exception as e:
            logger.error(f"Error in position update: {e}")
        time.sleep(0.1)  # Update every 100ms for more responsive feedback

# Start the position update thread
position_thread = threading.Thread(target=position_update_thread, daemon=True)
position_thread.start()

# API Routes

@app.route('/api/device/info', methods=['GET'])
def get_device_info():
    """Get information about the current device"""
    return jsonify({
        'type': 'real',
        'address': device.address,
        'port': config.get('device', {}).get('port')
    })

@app.route('/api/device/movement/<direction>', methods=['POST'])
def movement(direction):
    """Control movement in a specific direction"""
    speed = request.json.get('speed', 0x10) if request.is_json else 0x10
    
    try:
        # Stop commands are processed immediately to ensure safety
        if direction == 'stop':
            device.stop()
            return jsonify({'status': 'success', 'direction': direction})
        
        # No safety limits check needed
        
        # Other movement commands go through the queue        
        if direction == 'up':
            queue_command(device.move_up, speed=speed)
        elif direction == 'down':
            queue_command(device.move_down, speed=speed)
        elif direction == 'left':
            queue_command(device.move_left, speed=speed)
        elif direction == 'right':
            queue_command(device.move_right, speed=speed)
        else:
            return jsonify({'status': 'error', 'message': f'Invalid direction: {direction}'}), 400
        
        return jsonify({'status': 'success', 'direction': direction, 'speed': speed})
    except Exception as e:
        logger.error(f"Movement error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/device/position', methods=['GET'])
def get_position():
    """Get current position"""
    try:
        rel_pan, rel_tilt, raw_pan, raw_tilt = device.get_relative_position()
        return jsonify({
            'status': 'success',
            'rel_pan': rel_pan,
            'rel_tilt': rel_tilt,
            'raw_pan': raw_pan,
            'raw_tilt': raw_tilt
        })
    except Exception as e:
        logger.error(f"Position error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/device/position/absolute', methods=['POST'])
def absolute_position():
    """Move to absolute position"""
    if not request.is_json:
        return jsonify({'status': 'error', 'message': 'JSON payload required'}), 400
        
    data = request.json
    
    try:
        pan = data.get('pan')
        tilt = data.get('tilt')
        step_size = data.get('step_size')
        
        # Limit step size to 10 degrees
        if step_size is not None:
            if abs(step_size) > 10.0:
                logger.warning(f"Step size {step_size} exceeds limit of 10 degrees, limiting to 10.0")
                step_size = 10.0 if step_size > 0 else -10.0
        
        # Calculate target position based on current position and step size if provided
        if step_size is not None:
            current_position = device.query_position()
            if current_position[0] is not None and pan is None:
                pan = current_position[0] + step_size
            if current_position[1] is not None and tilt is None:
                tilt = current_position[1] + step_size
        
        def perform_abs_movement():
            if pan is not None:
                device.absolute_pan(pan)
            if tilt is not None:
                device.absolute_tilt(tilt)
        
        # Queue the absolute movement
        queue_command(perform_abs_movement)
        
        return jsonify({'status': 'success', 'pan': pan, 'tilt': tilt})
    except Exception as e:
        logger.error(f"Absolute position error: {e}")

        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/device/home', methods=['POST'])
def set_home():
    """Set home position"""
    try:
        queue_command(device.set_home_position)
        return jsonify({'status': 'success', 'message': 'Home position set'})
    except Exception as e:
        logger.error(f"Set home error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# WebSocket events
@socketio.on('connect')
def handle_connect():
    logger.info(f'Client connected: {request.sid}')
    # Send immediate position update to new client
    try:
        rel_pan, rel_tilt, raw_pan, raw_tilt = device.get_relative_position()
        emit('position_update', {
            'rel_pan': rel_pan,
            'rel_tilt': rel_tilt,
            'raw_pan': raw_pan,
            'raw_tilt': raw_tilt,
            'timestamp': time.time()
        })
    except Exception as e:
        logger.error(f"Error sending initial position: {e}")

@socketio.on('disconnect')
def handle_disconnect():
    logger.info(f'Client disconnected: {request.sid}')

@socketio.on('request_position')
def handle_request_position():
    try:
        rel_pan, rel_tilt, raw_pan, raw_tilt = device.get_relative_position()
        emit('position_update', {
            'rel_pan': rel_pan,
            'rel_tilt': rel_tilt,
            'raw_pan': raw_pan,
            'raw_tilt': raw_tilt,
            'timestamp': time.time()
        })
    except Exception as e:
        emit('error', {'message': str(e)})

if __name__ == '__main__':
    host = config['server'].get('host', '127.0.0.1')
    port = config['server'].get('port', 5000)
    
    logger.info(f"Starting Pan-Tilt API Server on {host}:{port}")
    logger.info(f"Device on port: {config.get('device', {}).get('port')}")
    
    # Use werkzeug's run_simple with threaded=True for better performance
    socketio.run(app, host=host, port=port, debug=False, allow_unsafe_werkzeug=True)


