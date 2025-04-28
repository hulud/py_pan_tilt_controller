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
from .models import MovementRequest, AbsolutePositionRequest, PositionResponse, ErrorResponse, SuccessResponse

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
                    # Get position with status information
                    rel_pan, rel_tilt, raw_pan, raw_tilt, status = controller.get_relative_position()
                    
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
        return jsonify({
            'type': 'real',
            'address': controller.protocol.address,
            'connection_type': controller.connection_type
        })
    
    # Movement endpoint
    @api_bp.route('/device/movement/<direction>', methods=['POST'])
    def movement(direction):
        """Control movement in a specific direction"""
        # Parse request
        if request.is_json:
            speed = request.json.get('speed', 0x10)
        else:
            speed = 0x10
        
        # Create and validate request model
        move_request = MovementRequest(direction=direction, speed=speed)
        if not move_request.validate():
            error = ErrorResponse(message=f"Invalid movement request: {direction}", code=400)
            return jsonify(error.to_dict()), 400
        
        try:
            # Stop commands are processed immediately
            if direction == 'stop':
                controller.stop()
                response = SuccessResponse(message="Movement stopped")
                return jsonify(response.to_dict())
            
            # Other movement commands go through the queue        
            if direction == 'up':
                queue_command(controller.move_up, speed=speed)
            elif direction == 'down':
                queue_command(controller.move_down, speed=speed)
            elif direction == 'left':
                queue_command(controller.move_left, speed=speed)
            elif direction == 'right':
                queue_command(controller.move_right, speed=speed)
            
            response = SuccessResponse(
                message=f"Movement {direction} initiated",
                data={'direction': direction, 'speed': speed}
            )
            return jsonify(response.to_dict())
        except Exception as e:
            logger.error(f"Movement error: {e}")
            error = ErrorResponse(message=str(e))
            return jsonify(error.to_dict()), 500
    
    # Position endpoint
    @api_bp.route('/device/position', methods=['GET'])
    def get_position():
        """Get current position"""
        try:
            rel_pan, rel_tilt, raw_pan, raw_tilt, status = controller.get_relative_position()
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
                tilt=data.get('tilt'),
                step_size=data.get('step_size')
            )
            
            if not pos_request.validate():
                error = ErrorResponse(
                    message="Invalid position request: must provide at least one of pan, tilt, or step_size",
                    code=400
                )
                return jsonify(error.to_dict()), 400
            
            # Limit step size to 10 degrees
            if pos_request.step_size is not None and abs(pos_request.step_size) > 10.0:
                logger.warning(f"Step size {pos_request.step_size} exceeds limit of 10 degrees, limiting to 10.0")
                pos_request.step_size = 10.0 if pos_request.step_size > 0 else -10.0
            
            # Calculate target position based on current position and step size if provided
            if pos_request.step_size is not None:
                current_position = controller.query_position()
                if current_position[0] is not None and pos_request.pan is None:
                    pos_request.pan = current_position[0] + pos_request.step_size
                if current_position[1] is not None and pos_request.tilt is None:
                    pos_request.tilt = current_position[1] + pos_request.step_size
            
            def perform_abs_movement():
                if pos_request.pan is not None:
                    controller.absolute_pan(pos_request.pan)
                if pos_request.tilt is not None:
                    controller.absolute_tilt(pos_request.tilt)
            
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
            queue_command(controller.set_home_position)
            response = SuccessResponse(message="Home position set")
            return jsonify(response.to_dict())
        except Exception as e:
            logger.error(f"Set home error: {e}")
            error = ErrorResponse(message=str(e))
            return jsonify(error.to_dict()), 500
    
    # Preset endpoints
    @api_bp.route('/device/presets/<int:preset_id>', methods=['POST'])
    def set_preset(preset_id):
        """Set a preset position"""
        try:
            queue_command(controller.set_preset, preset_id)
            response = SuccessResponse(
                message=f"Preset {preset_id} set",
                data={'preset_id': preset_id}
            )
            return jsonify(response.to_dict())
        except Exception as e:
            logger.error(f"Set preset error: {e}")
            error = ErrorResponse(message=str(e))
            return jsonify(error.to_dict()), 500
    
    @api_bp.route('/device/presets/<int:preset_id>/call', methods=['POST'])
    def call_preset(preset_id):
        """Call a preset position"""
        try:
            queue_command(controller.call_preset, preset_id)
            response = SuccessResponse(
                message=f"Preset {preset_id} called",
                data={'preset_id': preset_id}
            )
            return jsonify(response.to_dict())
        except Exception as e:
            logger.error(f"Call preset error: {e}")
            error = ErrorResponse(message=str(e))
            return jsonify(error.to_dict()), 500
    
    @api_bp.route('/device/presets/<int:preset_id>', methods=['DELETE'])
    def clear_preset(preset_id):
        """Clear a preset position"""
        try:
            queue_command(controller.clear_preset, preset_id)
            response = SuccessResponse(
                message=f"Preset {preset_id} cleared",
                data={'preset_id': preset_id}
            )
            return jsonify(response.to_dict())
        except Exception as e:
            logger.error(f"Clear preset error: {e}")
            error = ErrorResponse(message=str(e))
            return jsonify(error.to_dict()), 500
    
    # Optical endpoints
    @api_bp.route('/device/optical/<action>', methods=['POST'])
    def optical_control(action):
        """Control optical features (zoom/focus/iris)"""
        try:
            if action == 'zoom_in':
                queue_command(controller.zoom_in)
            elif action == 'zoom_out':
                queue_command(controller.zoom_out)
            elif action == 'focus_far':
                queue_command(controller.focus_far)
            elif action == 'focus_near':
                queue_command(controller.focus_near)
            elif action == 'iris_open':
                queue_command(controller.iris_open)
            elif action == 'iris_close':
                queue_command(controller.iris_close)
            else:
                error = ErrorResponse(message=f"Invalid optical action: {action}", code=400)
                return jsonify(error.to_dict()), 400
            
            response = SuccessResponse(
                message=f"Optical action {action} initiated",
                data={'action': action}
            )
            return jsonify(response.to_dict())
        except Exception as e:
            logger.error(f"Optical control error: {e}")
            error = ErrorResponse(message=str(e))
            return jsonify(error.to_dict()), 500
    
    # Auxiliary endpoints
    @api_bp.route('/device/aux/<int:aux_id>', methods=['POST'])
    def aux_control(aux_id):
        """Control auxiliary devices"""
        if not request.is_json:
            error = ErrorResponse(message="JSON payload required", code=400)
            return jsonify(error.to_dict()), 400
            
        data = request.json
        state = data.get('state')
        
        if state not in ['on', 'off']:
            error = ErrorResponse(message="State must be 'on' or 'off'", code=400)
            return jsonify(error.to_dict()), 400
        
        try:
            if state == 'on':
                queue_command(controller.aux_on, aux_id)
            else:
                queue_command(controller.aux_off, aux_id)
            
            response = SuccessResponse(
                message=f"Auxiliary {aux_id} turned {state}",
                data={'aux_id': aux_id, 'state': state}
            )
            return jsonify(response.to_dict())
        except Exception as e:
            logger.error(f"Auxiliary control error: {e}")
            error = ErrorResponse(message=str(e))
            return jsonify(error.to_dict()), 500
    
    # Reset endpoint
    @api_bp.route('/device/reset', methods=['POST'])
    def reset_device():
        """Reset the device"""
        try:
            queue_command(controller.remote_reset)
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
            rel_pan, rel_tilt, raw_pan, raw_tilt, status = controller.get_relative_position()
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
            rel_pan, rel_tilt, raw_pan, raw_tilt, status = controller.get_relative_position()
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
