"""
Base abstract class for connections.

This module defines the interface that all connection types must implement.
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Union, Callable


class ConnectionBase(ABC):
    """
    Abstract base class for connections to PTZ cameras.
    
    This class defines the interface that all connection implementations
    must provide to interact with physical devices.
    """
    
    @abstractmethod
    def open(self) -> bool:
        """
        Open the connection to the device.
        
        Returns:
            True if connection was successfully opened, False otherwise
        """
        pass
    
    @abstractmethod
    def close(self) -> bool:
        """
        Close the connection to the device.
        
        Returns:
            True if connection was successfully closed, False otherwise
        """
        pass
    
    @abstractmethod
    def is_open(self) -> bool:
        """
        Check if connection is currently open.
        
        Returns:
            True if connection is open, False otherwise
        """
        pass
    
    @abstractmethod
    def send(self, data: bytes) -> int:
        """
        Send data to the device.
        
        Args:
            data: Bytes to send
            
        Returns:
            Number of bytes sent
            
        Raises:
            ConnectionError: If the connection is not open or an error occurs
        """
        pass
    
    @abstractmethod
    def receive(self, size: int = 1024, timeout: float = 1.0) -> bytes:
        """
        Receive data from the device.
        
        Args:
            size: Maximum number of bytes to receive
            timeout: Maximum time to wait for data in seconds
            
        Returns:
            Received bytes
            
        Raises:
            ConnectionError: If the connection is not open or an error occurs
            TimeoutError: If no data is received within the timeout period
        """
        pass
    
    @abstractmethod
    def receive_until(self, 
                     terminator: bytes, 
                     max_size: int = 1024, 
                     timeout: float = 1.0) -> bytes:
        """
        Receive data until a specific terminator sequence is encountered.
        
        Args:
            terminator: Bytes sequence that marks the end of transmission
            max_size: Maximum number of bytes to receive
            timeout: Maximum time to wait for data in seconds
            
        Returns:
            Received bytes including the terminator
            
        Raises:
            ConnectionError: If the connection is not open or an error occurs
            TimeoutError: If terminator is not received within the timeout period
        """
        pass
    
    @property
    @abstractmethod
    def config(self) -> Dict[str, Any]:
        """
        Get the current connection configuration.
        
        Returns:
            Dictionary with configuration parameters
        """
        pass
    
    @abstractmethod
    def set_config(self, config: Dict[str, Any]) -> bool:
        """
        Update the connection configuration.
        
        Args:
            config: Dictionary with configuration parameters
            
        Returns:
            True if configuration was successfully updated, False otherwise
        """
        pass
    
    @abstractmethod
    def register_receive_callback(self, callback: Callable[[bytes], None]) -> bool:
        """
        Register a callback function to be called when data is received.
        
        Args:
            callback: Function that takes received bytes as argument
            
        Returns:
            True if callback was successfully registered, False otherwise
        """
        pass
    
    @abstractmethod
    def unregister_receive_callback(self) -> bool:
        """
        Unregister the currently active receive callback.
        
        Returns:
            True if callback was successfully unregistered, False otherwise
        """
        pass
    
    def __enter__(self):
        """Enable use with context manager"""
        self.open()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up when context manager exits"""
        self.close()
