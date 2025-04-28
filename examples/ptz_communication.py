"""
PTZ Controller Communication Example using BIT-CCTV Pelco-D parser
"""
import time
import binascii
import logging
import serial
import sys
import os

# Add the project root to the path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from src.protocol.pelco_parser import (
    parse_response, create_pan_query, create_tilt_query,
    create_absolute_pan_command, create_absolute_tilt_command,
    create_stop_command, format_command
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class PTZController:
    def __init__(self, port='COM3', baudrate=9600, address=1, timeout=0.5):
        """Initialize PTZ controller with serial parameters"""
        self.port = port
        self.baudrate = baudrate
        self.address = address
        self.timeout = timeout
        self.ser = None
    
    def connect(self):
        """Connect to the serial port"""
        try:
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=self.timeout
            )
            logger.info(f"Connected to {self.port} at {self.baudrate} bps")
            return True
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False
    
    def disconnect(self):
        """Close the serial connection"""
        if self.ser and self.ser.is_open:
            self.ser.close()
            logger.info("Disconnected from serial port")
    
    def send_command(self, cmd_bytes, description="", parse_result=True, extended_timeout=1.0):
        """Send a command and read the response
        
        Args:
            cmd_bytes: Command bytes to send
            description: Description for logging
            parse_result: Whether to parse the response
            extended_timeout: Longer timeout for reading response
            
        Returns:
            Parsed response data or raw bytes
        """
        if not self.ser or not self.ser.is_open:
            logger.error("Serial port not open")
            return None
        
        # Log the command
        cmd_hex = binascii.hexlify(cmd_bytes, ' ').decode().upper()
        logger.info(f"Sending: {description}")
        logger.info(f"TX: {cmd_hex} | {format_command(cmd_bytes)}")
        
        # Send the command
        self.ser.write(cmd_bytes)
        time.sleep(0.2)  # Short delay for processing
        
        # Read response (expected to be 5 bytes for BIT-CCTV)
        response = b''
        start_time = time.time()
        while time.time() - start_time < extended_timeout:
            if self.ser.in_waiting > 0:
                chunk = self.ser.read(self.ser.in_waiting)
                response += chunk
                time.sleep(0.1)  # Small delay for more data
            time.sleep(0.05)
        
        if not response:
            logger.warning("No response received")
            return None
        
        # Log the response
        resp_hex = binascii.hexlify(response, ' ').decode().upper()
        logger.info(f"RX: {resp_hex}")
        
        # Parse the response if requested
        if parse_result:
            result = parse_response(response)
            if result['valid']:
                if 'type' in result and result['type'] in ['pan_position', 'tilt_position']:
                    logger.info(f"Position: {result['position_formatted']}")
                    if not result['checksum_valid']:
                        logger.warning("⚠️ Checksum validation failed")
            else:
                logger.warning(f"Invalid response: {result.get('error', 'Unknown error')}")
            return result
        
        return response
    
    def get_pan_position(self):
        """Query current pan position"""
        cmd = create_pan_query(self.address)
        result = self.send_command(cmd, "Pan position query")
        if result and result['valid'] and result['type'] == 'pan_position':
            return result['position']
        return None
    
    def get_tilt_position(self):
        """Query current tilt position"""
        cmd = create_tilt_query(self.address)
        result = self.send_command(cmd, "Tilt position query")
        if result and result['valid'] and result['type'] == 'tilt_position':
            return result['position']
        return None
    
    def move_to_position(self, pan=None, tilt=None):
        """Move to specific pan and tilt positions"""
        if pan is not None:
            logger.info(f"Moving pan to {pan