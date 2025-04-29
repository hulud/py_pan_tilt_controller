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
    
    def validate(self) -> bool:
        """
        Validate the absolute position request.
        
        Returns:
            True if valid, False otherwise
        """
        # Either pan or tilt must be provided
        if self.pan is None and self.tilt is None:
            return False
            
        return True


@dataclass
class StepPositionRequest:
    """Request model for step-based position control"""
    
    step_pan: Optional[float] = None
    step_tilt: Optional[float] = None
    
    def validate(self) -> bool:
        """
        Validate the step position request.
        
        Returns:
            True if valid, False otherwise
        """
        # Either step_pan or step_tilt must be provided
        if self.step_pan is None and self.step_tilt is None:
            return False
            
        # Step sizes must be within limits
        if self.step_pan is not None and abs(self.step_pan) > 10.0:
            return False
            
        if self.step_tilt is not None and abs(self.step_tilt) > 10.0:
            return False
            
        return True


@dataclass
class PositionResponse:
    """Response model for position queries"""
    
    rel_pan: float
    rel_tilt: float
    raw_pan: float
    raw_tilt: float
    status: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary representation.
        
        Returns:
            Dictionary representation suitable for JSON serialization
        """
        result = {
            'status': 'success',
            'rel_pan': self.rel_pan,
            'rel_tilt': self.rel_tilt,
            'raw_pan': self.raw_pan,
            'raw_tilt': self.raw_tilt,
            'timestamp': None  # Will be filled in by client
        }
        
        # Add position status information if available
        if self.status:
            result['position_status'] = self.status
        else:
            # Legacy fallback status determination
            is_valid = self.raw_pan is not None and self.raw_tilt is not None
            result['position_status'] = {
                'pan_valid': is_valid,
                'tilt_valid': is_valid,
                'position_type': 'measured' if is_valid else 'estimated'
            }
            
        return result


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
