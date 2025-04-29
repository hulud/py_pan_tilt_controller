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
                timeout: float = 1.0,
                polling_rate: float = None,
                enable_polling: bool = True):
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
        self._polling_rate = polling_rate
        self._enable_polling = enable_polling
        
        # Serial connection object
        self._serial = None
        
        # Lock to serialize all serial port I/O
        self._io_lock = threading.Lock()
        
        # Callback management
        self._callback = None
        self._callback_thread = None
        self._callback_active = False
    
    def open(self) -> bool:
        """
        Open the serial connection with retry logic.
        
        Returns:
            True if successfully opened, False otherwise
        """
        import time
        
        # If there was a previous connection, ensure it's fully closed
        if self._serial is not None:
            try:
                self._serial.close()
                self._serial = None
                # Give the OS time to fully release the port
                time.sleep(0.5)
            except Exception as e:
                print(f"Error closing previous connection: {e}")
        
        # Try to open the connection with retries
        max_retries = 3
        retry_delay = 1.0
        
        for attempt in range(1, max_retries + 1):
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
                    timeout=self._timeout,
                    exclusive=True  # Request exclusive access to the port
                )
                
                # Validate connection is actually open
                if self._serial.is_open:
                    print(f"Successfully opened serial port {self._port} on attempt {attempt}")
                    return True
                else:
                    print(f"Serial port {self._port} not open after creation on attempt {attempt}")
                    self._serial = None
                    
            except serial.SerialException as e:
                if "PermissionError" in str(e) or "Access is denied" in str(e):
                    print(f"Access denied to port {self._port} on attempt {attempt}/{max_retries}: {e}")
                else:
                    print(f"Error opening serial port {self._port} on attempt {attempt}/{max_retries}: {e}")
                
                self._serial = None
                
                # Wait before retrying, unless this is the last attempt
                if attempt < max_retries:
                    print(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    
            except Exception as e:
                print(f"Unexpected error opening serial port {self._port} on attempt {attempt}/{max_retries}: {e}")
                self._serial = None
                
                # Wait before retrying, unless this is the last attempt
                if attempt < max_retries:
                    print(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
        
        print(f"Failed to open serial port {self._port} after {max_retries} attempts")
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
        
        with self._io_lock:
            # Enhanced debug print for sent data
            print(f"[SERIAL TX] >>> {' '.join(f'{b:02X}' for b in data)}|Len: {len(data)} bytes")
            print(f"[SERIAL TX] Command breakdown: {self._parse_pelco_command(data)}")
            
            return self._serial.write(data)
    
    def _format_as_ascii(self, data: bytes) -> str:
        """Format bytes as ASCII, showing printable characters and hex for others"""
        result = []
        for byte in data:
            if 32 <= byte <= 126:  # Printable ASCII
                result.append(chr(byte))
            else:
                result.append(f'\\x{byte:02X}')
        return ''.join(result)
    
    def _parse_pelco_command(self, data: bytes) -> str:
        """
        Parse Pelco D command structure for debugging
        
        Format: 0xFF add cmd1 cmd2 data1 data2 sum
        """
        if len(data) < 7 or data[0] != 0xFF:
            return "Not a valid Pelco D command"
            
        try:
            address = data[1]
            cmd1 = data[2]
            cmd2 = data[3]
            data1 = data[4]
            data2 = data[5]
            checksum = data[6]
            
            # Command analysis
            cmd_type = "Unknown"
            cmd_details = ""
            
            # Movement commands
            if cmd1 == 0x00:
                if cmd2 == 0x00 and data1 == 0x00 and data2 == 0x00:
                    cmd_type = "MOVEMENT"
                    cmd_details = "Stop"
                elif cmd2 == 0x02:
                    cmd_type = "MOVEMENT"
                    cmd_details = f"Pan Right (Speed: {data1}/63)"
                elif cmd2 == 0x04:
                    cmd_type = "MOVEMENT"
                    cmd_details = f"Pan Left (Speed: {data1}/63)"
                elif cmd2 == 0x08:
                    cmd_type = "MOVEMENT"
                    cmd_details = f"Tilt Up (Speed: {data2}/63)"
                elif cmd2 == 0x10:
                    cmd_type = "MOVEMENT"
                    cmd_details = f"Tilt Down (Speed: {data2}/63)"
                elif cmd2 == 0x0C:
                    cmd_type = "MOVEMENT"
                    cmd_details = f"Pan Left + Tilt Up (Pan speed: {data1}/63, Tilt speed: {data2}/63)"
                elif cmd2 == 0x14:
                    cmd_type = "MOVEMENT"
                    cmd_details = f"Pan Left + Tilt Down (Pan speed: {data1}/63, Tilt speed: {data2}/63)"
                elif cmd2 == 0x0A:
                    cmd_type = "MOVEMENT"
                    cmd_details = f"Pan Right + Tilt Up (Pan speed: {data1}/63, Tilt speed: {data2}/63)"
                elif cmd2 == 0x12:
                    cmd_type = "MOVEMENT"
                    cmd_details = f"Pan Right + Tilt Down (Pan speed: {data1}/63, Tilt speed: {data2}/63)"
                # Preset commands
                elif cmd2 == 0x03 and data1 == 0x00:
                    if data2 == 0x67:
                        cmd_type = "ZERO POINT"
                        cmd_details = "Set Pan Zero Point"
                    elif data2 == 0x68:
                        cmd_type = "ZERO POINT"
                        cmd_details = "Set Tilt Zero Point"
                    else:
                        cmd_type = "PRESET"
                        cmd_details = f"Set Preset {data2}"
                elif cmd2 == 0x07 and data1 == 0x00:
                    cmd_type = "PRESET"
                    cmd_details = f"Call Preset {data2}"
                elif cmd2 == 0x05 and data1 == 0x00:
                    cmd_type = "PRESET"
                    cmd_details = f"Clear Preset {data2}"
                # Position query commands
                elif cmd2 == 0x51 and data1 == 0x00 and data2 == 0x00:
                    cmd_type = "QUERY"
                    cmd_details = "Pan Position Query"
                elif cmd2 == 0x53 and data1 == 0x00 and data2 == 0x00:
                    cmd_type = "QUERY"
                    cmd_details = "Tilt Position Query"
                # Absolute position commands
                elif cmd2 == 0x4B:
                    value = (data1 << 8) | data2
                    angle = value / 100.0
                    cmd_type = "ABSOLUTE"
                    cmd_details = f"Pan to {angle:.2f}° (Raw: 0x{data1:02X}{data2:02X}={value})"
                elif cmd2 == 0x4D:
                    value = (data1 << 8) | data2
                    if value <= 18000:
                        angle = -value / 100.0
                    else:
                        angle = (36000 - value) / 100.0
                    cmd_type = "ABSOLUTE"
                    cmd_details = f"Tilt to {angle:.2f}° (Raw: 0x{data1:02X}{data2:02X}={value})"
                # Auxiliary commands
                elif cmd2 == 0x09 and data1 == 0x00:
                    cmd_type = "AUXILIARY"
                    cmd_details = f"AUX ON: {data2}"
                elif cmd2 == 0x0B and data1 == 0x00:
                    cmd_type = "AUXILIARY"
                    cmd_details = f"AUX OFF: {data2}"
                # Reset command
                elif cmd2 == 0x0F and data1 == 0x00 and data2 == 0x00:
                    cmd_type = "SYSTEM"
                    cmd_details = "Remote Reset"
            # Zoom commands
            elif cmd1 == 0x00 and cmd2 == 0x20:
                cmd_type = "OPTICAL"
                cmd_details = "Zoom In"
            elif cmd1 == 0x00 and cmd2 == 0x40:
                cmd_type = "OPTICAL"
                cmd_details = "Zoom Out"
            # Focus commands
            elif cmd1 == 0x00 and cmd2 == 0x80:
                cmd_type = "OPTICAL"
                cmd_details = "Focus Far"
            elif cmd1 == 0x01 and cmd2 == 0x00:
                cmd_type = "OPTICAL"
                cmd_details = "Focus Near"
            # Iris commands
            elif cmd1 == 0x02 and cmd2 == 0x00:
                cmd_type = "OPTICAL"
                cmd_details = "Iris Open"
            elif cmd1 == 0x04 and cmd2 == 0x00:
                cmd_type = "OPTICAL"
                cmd_details = "Iris Close"
            
            # Generic checksum calculation (sum all bytes except the last one)
            expected_sum = sum(data[:-1]) % 256
            checksum_status = "✓" if expected_sum == checksum else f"✗ (expected: {expected_sum:02X})"
            
            return (f"Addr: {address}, Cmc: {cmd1:02X} {cmd2:02X}, Dat: {data1:02X} {data2:02X}, " +
                    f"Type: {cmd_type} | {cmd_details}")
        except Exception as e:
            return f"Error parsing command: {e}"
    
    def receive(self, size: int = 5, timeout: float = None) -> bytes:
        """
        Receive data from the serial connection.
        Always reads exactly 5 bytes for BIT-CCTV position responses.
        
        Args:
            size: Number of bytes to read (default 5, usually ignored)
            timeout: Read timeout in seconds (overrides default)
            
        Returns:
            Received bytes (5 bytes if successful)
            
        Raises:
            ConnectionError: If connection is not open
            TimeoutError: If no data received within timeout
        """
        if not self.is_open():
            raise ConnectionError("Serial connection is not open")
        
        # Set temporary timeout if provided
        original_timeout = None
        
        try:
            with self._io_lock:
                if timeout is not None:
                    original_timeout = self._serial.timeout
                    self._serial.timeout = timeout
                
                # Always read exactly 5 bytes for position responses
                data = self._serial.read(5)
                
                # Debug prints for received data
                if data:
                    print(f"[SERIAL RX] <<< {' '.join(f'{b:02X}' for b in data)} | Len: {len(data)} bytes")
                    
                    # Parse as position response if we have full 5 bytes
                    if len(data) == 5 and (data[1] == 0x59 or data[1] == 0x5B):
                        response_info = self._parse_pelco_response(data)
                        print(f"[SERIAL RX] Response analysis: {response_info}")
                        
                        # Check if there's a checksum mismatch
                        if "✗" in response_info:  # Symbol used to indicate checksum failure
                            print(f"[SERIAL RX] Bad checksum detected, flushing input buffer")
                            self._serial.reset_input_buffer()  # Immediate flush on bad checksum
                    elif len(data) == 5:
                        print(f"[SERIAL RX] Invalid response format, flushing input buffer")
                        self._serial.reset_input_buffer()
                    elif len(data) < 5:
                        print(f"[SERIAL RX] Incomplete response ({len(data)}/5 bytes), flushing input buffer")
                        self._serial.reset_input_buffer()
                elif timeout is not None:
                    print(f"[SERIAL RX] No data received within timeout period ({timeout}s)")
                    raise TimeoutError("No data received within timeout period")
                
                # Restore original timeout if changed
                if original_timeout is not None:
                    self._serial.timeout = original_timeout
                    
            return data
        except TimeoutError:
            # Re-raise timeout error
            raise
        except Exception as e:
            print(f"[SERIAL RX] Unexpected error in receive: {e}")
            return bytes()
        finally:
            # Ensure timeout is restored even if an exception occurred inside the lock
            try:
                if original_timeout is not None and self._serial and self._serial.is_open:
                    with self._io_lock:
                        self._serial.timeout = original_timeout
            except Exception as e:
                print(f"[SERIAL RX] Error restoring timeout: {e}")
                
    def _parse_pelco_response(self, data: bytes) -> str:
        """
        Parse Pelco D response structure for debugging
        Format for position responses: XX 59 PMSB PLSB sum or XX 5B TMSB TLSB sum
        """
        if not data:
            return "Empty response"
            
        if len(data) != 5:
            return f"Invalid response length: {len(data)}, expected 5 bytes"
            
        # Parse 5-byte format
        xx = data[0]
        cmd = data[1]
        msb = data[2]
        lsb = data[3]
        checksum = data[4]
        
        # BIT-CCTV checksum calculation (cmd + data1 + data2)
        expected_sum = (cmd + msb + lsb) % 256
        # BIT-CCTV devices sometimes add 1 to the checksum
        checksum_status = "✓" if (checksum == expected_sum or checksum == expected_sum + 1) else f"✗ (expected: {expected_sum:02X})"
        
        # Pan position response (0x59)
        if cmd == 0x59:
            return f"Pan Position Response: XX={xx:02X}, PMSB={msb:02X}, PLSB={lsb:02X}"
        
        # Tilt position response (0x5B)
        elif cmd == 0x5B:
            return f"Tilt Position Response: XX={xx:02X}, TMSB={msb:02X}, TLSB={lsb:02X}"
        
        # Unknown command type for 5-byte message
        else:
            return f"Unknown 5-byte response: XX={xx:02X}, CMD={cmd:02X}, MSB={msb:02X}, LSB={lsb:02X}"
    
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
        
        try:
            with self._io_lock:
                if timeout is not None:
                    original_timeout = self._serial.timeout
                    self._serial.timeout = timeout
                
                # Use pyserial's read_until method
                data = self._serial.read_until(terminator, max_size)
                
                # Restore original timeout if changed
                if original_timeout is not None:
                    self._serial.timeout = original_timeout
                    
                # Check if terminator was found
                if not data.endswith(terminator) and timeout is not None:
                    raise TimeoutError("Terminator not received within timeout period")
                    
            return data
        finally:
            # Ensure timeout is restored even if an exception occurred inside the lock
            if original_timeout is not None and self._serial and self._serial.is_open:
                with self._io_lock:
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
            'timeout': self._timeout,
            'polling_rate': self._polling_rate,
            'enable_polling': self._enable_polling
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
            self._polling_rate = config.get('polling_rate', self._polling_rate)
            self._enable_polling = config.get('enable_polling', self._enable_polling)
            
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
                data = None
                with self._io_lock:
                    if self._serial.in_waiting:
                        data = self._serial.read(self._serial.in_waiting)
                
                if data and self._callback:
                    self._callback(data)
                    
                # Use configured polling rate or fallback to 0.01 if None
                sleep_time = self._polling_rate if self._polling_rate is not None else 0.01
                time.sleep(sleep_time)
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