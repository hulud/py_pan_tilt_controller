"""
API routes for PTZ camera control.

This module defines the REST API endpoints for controlling PTZ cameras.
"""
import time
import threading
import logging
from flask import Flask, request, jsonify, Blueprint
from flask_socketio import SocketIO, emit

from src.controller import PTZController
from .models import MovementRequest, AbsolutePositionRequest, StepPositionRequest, PositionResponse, ErrorResponse, SuccessResponse

logger = logging.getLogger(__name__)

# Command queue
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


def register_routes(app: Flask, socketio: SocketIO, controller: PTZController):
    # Store controller reference in socketio object for access after reloads
    socketio.controller = controller
    """
    Register all API routes.
    
    Args:
        app: Flask application instance
        socketio: SocketIO instance
        controller: PTZ controller instance
    """
    # Create blueprint for API routes
    api_bp = Blueprint('api', __name__, url_prefix='/api')
    
    # Position update thread
    def position_update_thread():
        """Thread that periodically emits position updates via WebSocket"""
        while True:
            try:
                # Use a try-except block to catch any errors in the position update
                try:
                    # Get the current controller instance (handles reloads)
                    current_controller = getattr(socketio, '_controller', controller)
                    
                    # Get position with status information
                    rel_pan, rel_tilt, status = current_controller.get_relative_position()
                    
                    # We don't have direct access to raw angles anymore
                    # Use relative angles as raw angles for backwards compatibility
                    raw_pan = rel_pan
                    raw_tilt = rel_tilt
                    
                    # Create response payload
                    position_data = {
                        'rel_pan': rel_pan,
                        'rel_tilt': rel_tilt,
                        'raw_pan': raw_pan,
                        'raw_tilt': raw_tilt,
                        'timestamp': time.time(),
                        'status': {
                            'pan_valid': status.get('pan_valid', False),
                            'tilt_valid': status.get('tilt_valid', False),
                            'position_type': 'measured' if (status.get('pan_valid', False) or status.get('tilt_valid', False)) else 'estimated'
                        }
                    }
                    
                    # Emit position update
                    socketio.emit('position_update', position_data)
                    
                except Exception as e:
                    # Log the error but don't let it crash the thread
                    logger.error(f"Error getting position data: {e}")
                    
                    # Emit default position values when position query fails
                    socketio.emit('position_update', {
                        'rel_pan': 0.0,
                        'rel_tilt': 0.0,
                        'raw_pan': 0.0,
                        'raw_tilt': 0.0,
                        'timestamp': time.time(),
                        'status': {
                            'pan_valid': False,
                            'tilt_valid': False,
                            'position_type': 'estimated',
                            'error': str(e)
                        }
                    })
            except Exception as e:
                logger.error(f"Error in position update thread: {e}")
            
            # Use a longer update interval to reduce pressure on the device
            time.sleep(0.25)  # Update every 250ms
    
    # Start the position update thread
    position_thread = threading.Thread(target=position_update_thread, daemon=True)
    position_thread.start()
    
    # Device info endpoint
    @api_bp.route('/device/info', methods=['GET'])
    def get_device_info():
        """Get information about the current device"""
        # Get the current controller instance (handles reloads)
        current_controller = getattr(socketio, '_controller', controller)
        
        return jsonify({
            'type': 'real',
            'address': current_controller.protocol.address,
            'connection_type': current_controller.connection_type
        })
    
    # Stop endpoint
    @api_bp.route('/device/stop', methods=['POST'])
    def stop():
        """Stop all camera movement"""
        try:
            # Get the current controller instance (handles reloads)
            current_controller = getattr(socketio, 'controller', controller)
            
            # Stop commands are processed immediately
            current_controller.stop()
            response = SuccessResponse(message="Movement stopped")
            return jsonify(response.to_dict())
        except Exception as e:
            logger.error(f"Stop error: {e}")
            error = ErrorResponse(message=str(e))
            return jsonify(error.to_dict()), 500
    
    # Position endpoint
    @api_bp.route('/device/position', methods=['GET'])
    def get_position():
        """Gets current camera position with angles relative to the home position (src/controller/ptz/core.py:261)"""
        try:
            # Get the current controller instance (handles reloads)
            current_controller = getattr(socketio, 'controller', controller)
            
            rel_pan, rel_tilt, status = current_controller.get_relative_position()
            # Use relative angles as raw angles for backwards compatibility
            raw_pan = rel_pan
            raw_tilt = rel_tilt
            position = PositionResponse(
                rel_pan=rel_pan,
                rel_tilt=rel_tilt,
                raw_pan=raw_pan,
                raw_tilt=raw_tilt,
                status={
                    'pan_valid': status.get('pan_valid', False),
                    'tilt_valid': status.get('tilt_valid', False),
                    'position_type': 'measured' if (status.get('pan_valid', False) or status.get('tilt_valid', False)) else 'estimated'
                }
            )
            return jsonify(position.to_dict())
        except Exception as e:
            logger.error(f"Position error: {e}")
            error = ErrorResponse(message=str(e))
            return jsonify(error.to_dict()), 500
    
    # Absolute position endpoint
    @api_bp.route('/device/position/absolute', methods=['POST'])
    def absolute_position():
        """Move to absolute position"""
        if not request.is_json:
            error = ErrorResponse(message="JSON payload required", code=400)
            return jsonify(error.to_dict()), 400
            
        data = request.json
        
        try:
            # Create and validate request model
            pos_request = AbsolutePositionRequest(
                pan=data.get('pan'),
                tilt=data.get('tilt')
            )
            
            if not pos_request.validate():
                error = ErrorResponse(
                    message="Invalid position request: must provide at least one of pan or tilt",
                    code=400
                )
                return jsonify(error.to_dict()), 400
            
            def perform_abs_movement():
                # Get the current controller instance (handles reloads)
                current_controller = getattr(socketio, 'controller', controller)
                
                if pos_request.pan is not None:
                    current_controller.absolute_pan(pos_request.pan)
                if pos_request.tilt is not None:
                    current_controller.absolute_tilt(pos_request.tilt)
            
            # Queue the absolute movement
            queue_command(perform_abs_movement)
            
            response = SuccessResponse(
                message="Absolute position movement initiated",
                data={'pan': pos_request.pan, 'tilt': pos_request.tilt}
            )
            return jsonify(response.to_dict())
        except Exception as e:
            logger.error(f"Absolute position error: {e}")
            error = ErrorResponse(message=str(e))
            return jsonify(error.to_dict()), 500
    
    # Home position endpoint
    @api_bp.route('/device/home', methods=['POST'])
    def set_home():
        """Set home position"""
        try:
            # Get the current controller instance (handles reloads)
            current_controller = getattr(socketio, 'controller', controller)
            
            queue_command(current_controller.set_home_position)
            response = SuccessResponse(message="Home position set")
            return jsonify(response.to_dict())
        except Exception as e:
            logger.error(f"Set home error: {e}")
            error = ErrorResponse(message=str(e))
            return jsonify(error.to_dict()), 500
    
    # Step position endpoint
    @api_bp.route('/device/position/step', methods=['POST'])
    def step_position():
        """Move by incremental step size"""
        if not request.is_json:
            error = ErrorResponse(message="JSON payload required", code=400)
            return jsonify(error.to_dict()), 400
            
        data = request.json
        
        try:
            # Create and validate request model
            pos_request = StepPositionRequest(
                step_pan=data.get('step_pan'),
                step_tilt=data.get('step_tilt')
            )
            
            if not pos_request.validate():
                error = ErrorResponse(
                    message="Invalid step request: must provide at least one of step_pan or step_tilt within limits",
                    code=400
                )
                return jsonify(error.to_dict()), 400
            
            # Get the current controller instance
            current_controller = getattr(socketio, 'controller', controller)
            
            # Get current position
            current_position = current_controller.query_position()
            current_pan, current_tilt = current_position
            
            # Default to zero if current position is None
            if current_pan is None:
                current_pan = 0.0
            if current_tilt is None:
                current_tilt = 0.0
            
            # Calculate target position
            target_pan = None
            target_tilt = None
            
            if pos_request.step_pan is not None:
                target_pan = current_pan + pos_request.step_pan
            
            if pos_request.step_tilt is not None:
                target_tilt = current_tilt + pos_request.step_tilt
            
            def perform_step_movement():
                # Get the current controller instance (handles reloads)
                current_controller = getattr(socketio, 'controller', controller)
                
                if target_pan is not None:
                    current_controller.absolute_pan(target_pan)
                if target_tilt is not None:
                    current_controller.absolute_tilt(target_tilt)
            
            # Queue the step movement
            queue_command(perform_step_movement)
            
            response = SuccessResponse(
                message="Step position movement initiated",
                data={
                    'from_pan': current_pan,
                    'from_tilt': current_tilt,
                    'to_pan': target_pan,
                    'to_tilt': target_tilt,
                    'step_pan': pos_request.step_pan,
                    'step_tilt': pos_request.step_tilt
                }
            )
            return jsonify(response.to_dict())
        except Exception as e:
            logger.error(f"Step position error: {e}")
            error = ErrorResponse(message=str(e))
            return jsonify(error.to_dict()), 500
    
    # Reset endpoint
    @api_bp.route('/device/reset', methods=['POST'])
    def reset_device():
        """Reset the device"""
        try:
            # Get the current controller instance (handles reloads)
            current_controller = getattr(socketio, 'controller', controller)
            
            queue_command(current_controller.remote_reset)
            response = SuccessResponse(message="Device reset initiated")
            return jsonify(response.to_dict())
        except Exception as e:
            logger.error(f"Reset error: {e}")
            error = ErrorResponse(message=str(e))
            return jsonify(error.to_dict()), 500
    
    # WebSocket events
    @socketio.on('connect')
    def handle_connect():
        logger.info(f'Client connected: {request.sid}')
        # Send immediate position update to new client
        try:
            # Get the current controller instance (handles reloads)
            current_controller = getattr(socketio, 'controller', controller)
            
            rel_pan, rel_tilt, status = current_controller.get_relative_position()
            # Use relative angles as raw angles for backwards compatibility
            raw_pan = rel_pan
            raw_tilt = rel_tilt
            emit('position_update', {
                'rel_pan': rel_pan,
                'rel_tilt': rel_tilt,
                'raw_pan': raw_pan,
                'raw_tilt': raw_tilt,
                'timestamp': time.time(),
                'status': {
                    'pan_valid': status.get('pan_valid', False),
                    'tilt_valid': status.get('tilt_valid', False),
                    'position_type': 'measured' if (status.get('pan_valid', False) or status.get('tilt_valid', False)) else 'estimated'
                }
            })
        except Exception as e:
            logger.error(f"Error sending initial position: {e}")
            emit('error', {'message': str(e), 'source': 'connect'})

    @socketio.on('disconnect')
    def handle_disconnect():
        logger.info(f'Client disconnected: {request.sid}')

    @socketio.on('request_position')
    def handle_request_position():
        try:
            # Get the current controller instance (handles reloads)
            current_controller = getattr(socketio, 'controller', controller)
            
            rel_pan, rel_tilt, status = current_controller.get_relative_position()
            # Use relative angles as raw angles for backwards compatibility
            raw_pan = rel_pan
            raw_tilt = rel_tilt
            emit('position_update', {
                'rel_pan': rel_pan,
                'rel_tilt': rel_tilt,
                'raw_pan': raw_pan,
                'raw_tilt': raw_tilt,
                'timestamp': time.time(),
                'status': {
                    'pan_valid': status.get('pan_valid', False),
                    'tilt_valid': status.get('tilt_valid', False),
                    'position_type': 'measured' if (status.get('pan_valid', False) or status.get('tilt_valid', False)) else 'estimated'
                }
            })
        except Exception as e:
            logger.error(f"Error in request_position handler: {e}")
            emit('error', {
                'message': str(e),
                'source': 'request_position',
                'timestamp': time.time()
            })
    
    # Register the blueprint
    app.register_blueprint(api_bp)
