"""
Connection module for PTZ camera control systems.

This module provides abstract and concrete connection implementations
for serial connections to PTZ cameras.
"""

from .base import ConnectionBase
from .serial_conn import SerialConnection
from .simulator_conn import SimulatorConnection

__all__ = [
    'ConnectionBase',
    'SerialConnection',
    'SimulatorConnection',
]
