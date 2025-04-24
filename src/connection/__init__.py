"""
Connection module for PTZ camera control systems.

This module provides abstract and concrete connection implementations
for different types of physical connections to PTZ cameras.
"""

from .base import ConnectionBase
from .serial_conn import SerialConnection
from .network_conn import NetworkConnection

__all__ = [
    'ConnectionBase',
    'SerialConnection',
    'NetworkConnection',
]
