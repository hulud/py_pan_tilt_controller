"""
Serial connection implementation for PTZ cameras.

This module provides a concrete implementation of ConnectionBase
for serial connections (RS485/RS422) to PTZ cameras.
"""
import serial
import time
import threading
from typing import Optional, Dict, Any, Union, Callable, Tuple
from .base import ConnectionBase


class SerialConnection(ConnectionBase):
    """
    Serial connection implementation for PTZ cameras.
    
    Provides connection functionality over RS485/RS422 serial interfaces,
    which are commonly used for PTZ camera control.
    """
    
    def __init__(self, 
                port: str = 'COM3', 
                baudrate: int = 9600, 
                data_bits: int = 8,
                stop_bits: int = 1,
                parity: str = 'N',
                timeout: float = 1.0):
        """
        Initialize serial connection.
        
        Args:
            port: Serial port name
            baudrate: Communication speed
            data_bits: Number of data bits (5-8)
            stop_bits: Number of stop bits (1, 1.5, 2)
            parity: Parity checking ('N', 'E', 'O', 'M', 'S')
            timeout: Read timeout in seconds
        """
        self._port = port
        self._baudrate = baudrate
        self._data_bits = data_bits
        self._stop_bits = stop_bits
        self._parity = parity
        self._timeout = timeout
        
        # Serial connection object
        self._serial = None
        
        # Callback management
        self._callback = None
        self._callback_thread = None
        self._callback_active = False
    
    def open(self) -> bool:
        """
        Open the serial connection.
        
        Returns:
            True if successfully opened, False otherwise
        """
        try:
            # Convert data bits
            if self._data_bits == 5:
                data_bits = serial.FIVEBITS
            elif self._data_bits == 6:
                data_bits = serial.SIXBITS
            elif self._data_bits == 7:
                data_bits = serial.SEVENBITS
            else:
                data_bits = serial.EIGHTBITS
                
            # Convert stop bits
            if self._stop_bits == 1:
                stop_bits = serial.STOPBITS_ONE
            elif self._stop_bits == 1.5:
                stop_bits = serial.STOPBITS_ONE_POINT_FIVE
            else:
                stop_bits = serial.STOPBITS_TWO
                
            # Convert parity
            if self._parity.upper() == 'N':
                parity = serial.PARITY_NONE
            elif self._parity.upper() == 'E':
                parity = serial.PARITY_EVEN
            elif self._parity.upper() == 'O':
                parity = serial.PARITY_ODD
            elif self._parity.upper() == 'M':
                parity = serial.PARITY_MARK
            else:
                parity = serial.PARITY_SPACE
            
            # Create and open serial connection
            self._serial = serial.Serial(
                port=self._port,
                baudrate=self._baudrate,
                bytesize=data_bits,
                parity=parity,
                stopbits=stop_bits,
                timeout=self._timeout
            )
            
            return True
        except Exception as e:
            print(f"Error opening serial port: {e}")
            self._serial = None
            return False
    
    def close(self) -> bool:
        """
        Close the serial connection.
        
        Returns:
            True if successfully closed, False otherwise
        """
        try:
            if self._serial and self._serial.is_open:
                # Stop callback thread if active
                if self._callback_active:
                    self.unregister_receive_callback()
                
                # Close the connection
                self._serial.close()
                self._serial = None
            return True
        except Exception as e:
            print(f"Error closing serial port: {e}")
            return False
    
    def is_open(self) -> bool:
        """
        Check if the serial connection is open.
        
        Returns:
            True if connection is open, False otherwise
        """
        return self._serial is not None and self._serial.is_open
    
    def send(self, data: bytes) -> int:
        """
        Send data over the serial connection.
        
        Args:
            data: Bytes to send
            
        Returns:
            Number of bytes sent
            
        Raises:
            ConnectionError: If connection is not open
        """
        if not self.is_open():
            raise ConnectionError("Serial connection is not open")
        
        return self._serial.write(data)
    
    def receive(self, size: int = 1024, timeout: float = None) -> bytes:
        """
        Receive data from the serial connection.
        
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
            raise ConnectionError("Serial connection is not open")
        
        # Set temporary timeout if provided
        original_timeout = None
        if timeout is not None:
            original_timeout = self._serial.timeout
            self._serial.timeout = timeout
        
        try:
            # Read available data or wait for data
            data = self._serial.read(size)
            
            # Check for timeout (no data received)
            if not data and timeout is not None:
                raise TimeoutError("No data received within timeout period")
                
            return data
        finally:
            # Restore original timeout if changed
            if original_timeout is not None:
                self._serial.timeout = original_timeout
    
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
            raise ConnectionError("Serial connection is not open")
        
        # Set temporary timeout if provided
        original_timeout = None
        if timeout is not None:
            original_timeout = self._serial.timeout
            self._serial.timeout = timeout
        
        try:
            # Use pyserial's read_until method
            data = self._serial.read_until(terminator, max_size)
            
            # Check if terminator was found
            if not data.endswith(terminator) and timeout is not None:
                raise TimeoutError("Terminator not received within timeout period")
                
            return data
        finally:
            # Restore original timeout if changed
            if original_timeout is not None:
                self._serial.timeout = original_timeout
    
    @property
    def config(self) -> Dict[str, Any]:
        """
        Get the current serial configuration.
        
        Returns:
            Dictionary with configuration parameters
        """
        return {
            'port': self._port,
            'baudrate': self._baudrate,
            'data_bits': self._data_bits,
            'stop_bits': self._stop_bits,
            'parity': self._parity,
            'timeout': self._timeout
        }
    
    def set_config(self, config: Dict[str, Any]) -> bool:
        """
        Update the serial configuration.
        
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
            self._port = config.get('port', self._port)
            self._baudrate = config.get('baudrate', self._baudrate)
            self._data_bits = config.get('data_bits', self._data_bits)
            self._stop_bits = config.get('stop_bits', self._stop_bits)
            self._parity = config.get('parity', self._parity)
            self._timeout = config.get('timeout', self._timeout)
            
            # Reopen connection if it was open
            if was_open:
                return self.open()
                
            return True
        except Exception as e:
            print(f"Error updating serial configuration: {e}")
            
            # Restore old configuration
            self._port = old_config['port']
            self._baudrate = old_config['baudrate']
            self._data_bits = old_config['data_bits']
            self._stop_bits = old_config['stop_bits']
            self._parity = old_config['parity']
            self._timeout = old_config['timeout']
            
            # Reopen connection if it was open
            if was_open:
                self.open()
                
            return False
    
    def _callback_loop(self):
        """Background thread for receive callback"""
        while self._callback_active and self._serial and self._serial.is_open:
            try:
                if self._serial.in_waiting:
                    data = self._serial.read(self._serial.in_waiting)
                    if data and self._callback:
                        self._callback(data)
                time.sleep(0.01)  # Short sleep to prevent CPU hogging
            except Exception as e:
                print(f"Error in serial callback loop: {e}")
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
