"""
Network connection implementation for PTZ cameras.

This module provides a concrete implementation of ConnectionBase
for network connections to PTZ cameras.
"""
import socket
import threading
import time
import select
from typing import Optional, Dict, Any, Union, Callable, Tuple
from .base import ConnectionBase


class NetworkConnection(ConnectionBase):
    """
    Network connection implementation for PTZ cameras.
    
    Provides connection functionality over IP networks to PTZ cameras
    that support network control.
    """
    
    def __init__(self, 
                ip: str = '192.168.1.60', 
                port: int = 80,
                timeout: float = 1.0):
        """
        Initialize network connection.
        
        Args:
            ip: Camera IP address
            port: Camera port
            timeout: Connection timeout in seconds
        """
        self._ip = ip
        self._port = port
        self._timeout = timeout
        
        # Socket connection object
        self._socket = None
        
        # Callback management
        self._callback = None
        self._callback_thread = None
        self._callback_active = False
    
    def open(self) -> bool:
        """
        Open the network connection.
        
        Returns:
            True if successfully opened, False otherwise
        """
        try:
            # Create socket
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.settimeout(self._timeout)
            
            # Connect to device
            self._socket.connect((self._ip, self._port))
            
            return True
        except Exception as e:
            print(f"Error opening network connection: {e}")
            self._socket = None
            return False
    
    def close(self) -> bool:
        """
        Close the network connection.
        
        Returns:
            True if successfully closed, False otherwise
        """
        try:
            if self._socket:
                # Stop callback thread if active
                if self._callback_active:
                    self.unregister_receive_callback()
                
                # Close the connection
                self._socket.close()
                self._socket = None
            return True
        except Exception as e:
            print(f"Error closing network connection: {e}")
            return False
    
    def is_open(self) -> bool:
        """
        Check if the network connection is open.
        
        Returns:
            True if connection is open, False otherwise
        """
        return self._socket is not None
    
    def send(self, data: bytes) -> int:
        """
        Send data over the network connection.
        
        Args:
            data: Bytes to send
            
        Returns:
            Number of bytes sent
            
        Raises:
            ConnectionError: If connection is not open
        """
        if not self.is_open():
            raise ConnectionError("Network connection is not open")
        
        return self._socket.send(data)
    
    def receive(self, size: int = 1024, timeout: float = None) -> bytes:
        """
        Receive data from the network connection.
        
        Args:
            size: Maximum number of bytes to read
            timeout: Read timeout in seconds (overrides default)
            
        Returns:
            Received bytes
            
        Raises:
            ConnectionError: If connection is not open
            TimeoutError: If no data received within timeout
        """
        if not self.is_open():
            raise ConnectionError("Network connection is not open")
        
        # Set temporary timeout if provided
        original_timeout = None
        if timeout is not None:
            original_timeout = self._socket.gettimeout()
            self._socket.settimeout(timeout)
        
        try:
            # Check if data is available
            ready, _, _ = select.select([self._socket], [], [], timeout or self._timeout)
            
            if not ready:
                raise TimeoutError("No data received within timeout period")
            
            # Read data
            data = self._socket.recv(size)
            return data
        finally:
            # Restore original timeout if changed
            if original_timeout is not None:
                self._socket.settimeout(original_timeout)
    
    def receive_until(self, 
                     terminator: bytes, 
                     max_size: int = 1024, 
                     timeout: float = None) -> bytes:
        """
        Receive data until a specific terminator sequence is encountered.
        
        Args:
            terminator: Bytes sequence that marks the end of transmission
            max_size: Maximum number of bytes to receive
            timeout: Maximum time to wait for data in seconds
            
        Returns:
            Received bytes including the terminator
            
        Raises:
            ConnectionError: If connection is not open
            TimeoutError: If terminator not received within timeout
        """
        if not self.is_open():
            raise ConnectionError("Network connection is not open")
        
        # Set temporary timeout if provided
        original_timeout = None
        if timeout is not None:
            original_timeout = self._socket.gettimeout()
            self._socket.settimeout(timeout)
        
        try:
            # Receive until terminator or max size
            buffer = bytearray()
            start_time = time.time()
            timeout_value = timeout or self._timeout
            
            while len(buffer) < max_size:
                # Check for timeout
                if timeout_value is not None and time.time() - start_time > timeout_value:
                    raise TimeoutError("Terminator not received within timeout period")
                
                # Check if data is available for reading
                ready, _, _ = select.select([self._socket], [], [], 0.1)
                if not ready:
                    continue
                
                # Read chunk
                chunk = self._socket.recv(min(1024, max_size - len(buffer)))
                if not chunk:  # Connection closed
                    break
                    
                buffer.extend(chunk)
                
                # Check for terminator
                if terminator in buffer:
                    break
            
            # Check if terminator was found
            if terminator not in buffer and timeout is not None:
                raise TimeoutError("Terminator not received within timeout period")
                
            return bytes(buffer)
        finally:
            # Restore original timeout if changed
            if original_timeout is not None:
                self._socket.settimeout(original_timeout)
    
    @property
    def config(self) -> Dict[str, Any]:
        """
        Get the current network configuration.
        
        Returns:
            Dictionary with configuration parameters
        """
        return {
            'ip': self._ip,
            'port': self._port,
            'timeout': self._timeout
        }
    
    def set_config(self, config: Dict[str, Any]) -> bool:
        """
        Update the network configuration.
        
        Args:
            config: Dictionary with configuration parameters
            
        Returns:
            True if configuration was successfully updated, False otherwise
        """
        # Store current configuration to restore on failure
        old_config = self.config
        was_open = self.is_open()
        
        try:
            # Close connection if open
            if was_open:
                self.close()
            
            # Update configuration
            self._ip = config.get('ip', self._ip)
            self._port = config.get('port', self._port)
            self._timeout = config.get('timeout', self._timeout)
            
            # Reopen connection if it was open
            if was_open:
                return self.open()
                
            return True
        except Exception as e:
            print(f"Error updating network configuration: {e}")
            
            # Restore old configuration
            self._ip = old_config['ip']
            self._port = old_config['port']
            self._timeout = old_config['timeout']
            
            # Reopen connection if it was open
            if was_open:
                self.open()
                
            return False
    
    def _callback_loop(self):
        """Background thread for receive callback"""
        while self._callback_active and self._socket:
            try:
                # Check if data is available
                ready, _, _ = select.select([self._socket], [], [], 0.1)
                
                if ready:
                    data = self._socket.recv(1024)
                    if data and self._callback:
                        self._callback(data)
                    elif not data:
                        # Connection closed
                        break
            except Exception as e:
                print(f"Error in network callback loop: {e}")
                break
    
    def register_receive_callback(self, callback: Callable[[bytes], None]) -> bool:
        """
        Register a callback function to be called when data is received.
        
        Args:
            callback: Function that takes received bytes as argument
            
        Returns:
            True if callback was successfully registered, False otherwise
        """
        if not self.is_open():
            return False
        
        # Stop existing callback if active
        if self._callback_active:
            self.unregister_receive_callback()
        
        # Set up new callback
        self._callback = callback
        self._callback_active = True
        self._callback_thread = threading.Thread(target=self._callback_loop, daemon=True)
        self._callback_thread.start()
        
        return True
    
    def unregister_receive_callback(self) -> bool:
        """
        Unregister the currently active receive callback.
        
        Returns:
            True if callback was successfully unregistered, False otherwise
        """
        if not self._callback_active:
            return True
        
        self._callback_active = False
        if self._callback_thread:
            self._callback_thread.join(timeout=1.0)
            self._callback_thread = None
        
        self._callback = None
        return True
