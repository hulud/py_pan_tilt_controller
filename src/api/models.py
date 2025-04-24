"""
Data models for API requests and responses.
"""
from typing import Optional, List, Dict, Any, Union
from dataclasses import dataclass


@dataclass
class MovementRequest:
    """Request model for movement controls"""
    
    direction: str
    speed: int = 0x20
    
    def validate(self) -> bool:
        """
        Validate the movement request.
        
        Returns:
            True if valid, False otherwise
        """
        if self.direction not in ['up', 'down', 'left', 'right', 'stop']:
            return False
            
        if not 0 <= self.speed <= 0x3F:
            return False
            
        return True


@dataclass
class AbsolutePositionRequest:
    """Request model for absolute position control"""
    
    pan: Optional[float] = None
    tilt: Optional[float] = None
    step_size: Optional[float] = None
    
    def validate(self) -> bool:
        """
        Validate the absolute position request.
        
        Returns:
            True if valid, False otherwise
        """
        # Either pan, tilt, or step_size must be provided
        if self.pan is None and self.tilt is None and self.step_size is None:
            return False
            
        # If step_size provided, it must be within limits
        if self.step_size is not None and abs(self.step_size) > 10.0:
            return False
            
        return True


@dataclass
class PositionResponse:
    """Response model for position queries"""
    
    rel_pan: Optional[float]
    rel_tilt: Optional[float]
    raw_pan: Optional[float]
    raw_tilt: Optional[float]
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary representation.
        
        Returns:
            Dictionary representation suitable for JSON serialization
        """
        return {
            'status': 'success' if self.raw_pan is not None and self.raw_tilt is not None else 'error',
            'rel_pan': self.rel_pan,
            'rel_tilt': self.rel_tilt,
            'raw_pan': self.raw_pan,
            'raw_tilt': self.raw_tilt
        }


@dataclass
class ErrorResponse:
    """Standard error response model"""
    
    message: str
    code: int = 500
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary representation.
        
        Returns:
            Dictionary representation suitable for JSON serialization
        """
        return {
            'status': 'error',
            'message': self.message,
            'code': self.code
        }


@dataclass
class SuccessResponse:
    """Standard success response model"""
    
    message: str
    data: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary representation.
        
        Returns:
            Dictionary representation suitable for JSON serialization
        """
        response = {
            'status': 'success',
            'message': self.message
        }
        
        if self.data:
            response.update(self.data)
            
        return response
