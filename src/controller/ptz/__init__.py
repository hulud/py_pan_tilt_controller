"""
Public façade for the PTZ sub-package.

Keeps backward compatibility with the original import path:
    from src.controller.ptz import PTZController
"""

from .core import PTZController

__all__ = ["PTZController"]
