"""
API module for PTZ camera control.

This module provides a REST API for controlling PTZ cameras.
"""

from .server import create_app
from .routes import register_routes
from .models import PositionResponse, MovementRequest, AbsolutePositionRequest

__all__ = [
    'create_app',
    'register_routes',
    'PositionResponse',
    'MovementRequest',
    'AbsolutePositionRequest'
]
