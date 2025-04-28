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
        
        # Enhanced debug print for sent data
        print(f"[SERIAL TX] >>> {' '.join(f'{b:02X}' for b in data)} | ASCII: {self._format_as_ascii(data)} | Length: {len(data)} bytes")
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
            
            # Calculate expected checksum to verify
            expected_sum = sum([address, cmd1, cmd2, data1, data2]) % 256
            checksum_status = "✓" if expected_sum == checksum else f"✗ (expected: {expected_sum:02X})"
            
            return (f"Address: {address}, Command: {cmd1:02X} {cmd2:02X}, Data: {data1:02X} {data2:02X}, " +
                    f"Checksum: {checksum:02X} {checksum_status} | Type: {cmd_type} | {cmd_details}")
        except Exception as e:
            return f"Error parsing command: {e}"
    
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
            try:
                data = self._serial.read(size)
            except Exception as e:
                print(f"[SERIAL RX] Error reading from serial port: {e}")
                return bytes()
                
            # Debug prints for received data
            if data:
                try:
                    print(f"[SERIAL RX] <<< {' '.join(f'{b:02X}' for b in data)} | ASCII: {self._format_as_ascii(data)} | Length: {len(data)} bytes")
                    
                    # Try to parse the response
                    if len(data) >= 7 and (0x59 in data or 0x5B in data):  # Check if it might be a position response
                        print(f"[SERIAL RX] Response analysis: {self._parse_pelco_response(data)}")
                except Exception as e:
                    print(f"[SERIAL RX] Error in debug printing: {e}")
            elif timeout is not None:
                print(f"[SERIAL RX] No data received within timeout period ({timeout}s)")
                raise TimeoutError("No data received within timeout period")
                
            return data
        except TimeoutError:
            # Re-raise timeout error
            raise
        except Exception as e:
            print(f"[SERIAL RX] Unexpected error in receive: {e}")
            return bytes()
        finally:
            # Restore original timeout if changed
            try:
                if original_timeout is not None and self._serial and self._serial.is_open:
                    self._serial.timeout = original_timeout
            except Exception as e:
                print(f"[SERIAL RX] Error restoring timeout: {e}")
                
    def _parse_pelco_response(self, data: bytes) -> str:
        """
        Parse Pelco D response structure for debugging
        """
        try:
            # Handle empty data
            if not data:
                return "Empty response"
                
            # Check for pan position response (0x59)
            if 0x59 in data:
                idx = data.index(0x59)
                if len(data) >= idx + 3:
                    try:
                        # Extract MSB and LSB bytes
                        msb = data[idx + 1]
                        lsb = data[idx + 2]
                        
                        # Calculate raw data value (PMSB*256 + PLSB)
                        raw_value = (msb << 8) | lsb
                        
                        # Calculate angle according to the protocol spec: Pan angle = raw_value / 100.0
                        pan_angle = (raw_value / 100.0) % 360.0
                        
                        return f"Pan Position Response: Raw=0x{msb:02X}{lsb:02X}={raw_value}, Angle={pan_angle:.2f}°"
                    except Exception as e:
                        return f"Error parsing pan position response at index {idx}: {e}"
                else:
                    return f"Incomplete pan position response: found 0x59 at position {idx} but not enough data follows"
            
            # Check for tilt position response (0x5B)
            elif 0x5B in data:
                idx = data.index(0x5B)
                if len(data) >= idx + 3:
                    try:
                        # Extract MSB and LSB bytes
                        msb = data[idx + 1]
                        lsb = data[idx + 2]
                        
                        # Calculate raw data value (TMSB*256 + TLSB)
                        raw_value = (msb << 8) | lsb
                        
                        # Calculate angle according to protocol spec
                        if raw_value > 18000:
                            tilt_data = 36000 - raw_value
                            tilt_angle = tilt_data / 100.0
                        else:
                            tilt_data = -raw_value
                            tilt_angle = tilt_data / 100.0
                        
                        return f"Tilt Position Response: Raw=0x{msb:02X}{lsb:02X}={raw_value}, Calculated={tilt_data}, Angle={tilt_angle:.2f}°"
                    except Exception as e:
                        return f"Error parsing tilt position response at index {idx}: {e}"
                else:
                    return f"Incomplete tilt position response: found 0x5B at position {idx} but not enough data follows"
            
            # Check if it might be a complete response with checksum
            if len(data) >= 7 and data[0] == 0xFF:
                try:
                    address = data[1]
                    cmd1 = data[2]
                    cmd2 = data[3]
                    data1 = data[4]
                    data2 = data[5]
                    checksum = data[6]
                    
                    # Calculate expected checksum
                    expected_sum = sum([address, cmd1, cmd2, data1, data2]) % 256
                    checksum_status = "✓" if expected_sum == checksum else f"✗ (expected: {expected_sum:02X})"
                    
                    return f"Complete Response: Addr={address}, Cmd={cmd1:02X}{cmd2:02X}, Data={data1:02X}{data2:02X}, Checksum={checksum:02X} {checksum_status}"
                except Exception as e:
                    return f"Error parsing complete response: {e}"
            
            return f"Unknown response format: {' '.join(f'{b:02X}' for b in data)}"
        except Exception as e:
            return f"Error parsing response: {e}, data: {data.hex() if data else 'None'}"
    
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
