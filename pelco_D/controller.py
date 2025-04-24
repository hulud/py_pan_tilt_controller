#!/usr/bin/env python3
import serial
import time
import threading
from .position import PositionMixin
from .movement import MovementMixin
from .absolute_position import AbsolutePositionMixin
from .presets import PresetsMixin
from .auxiliary import AuxiliaryMixin
from .optical import OpticalMixin
from .advanced import AdvancedMixin

class PelcoDController(PositionMixin, MovementMixin, AbsolutePositionMixin, 
                       PresetsMixin, AuxiliaryMixin, OpticalMixin, AdvancedMixin):
    """
    Pelco D Protocol Camera Controller - NO SAFETY FEATURES
    Class uses multiple inheritance with mixins to organize functionality.
    """
    
    def __init__(self, port='COM3', baudrate=9600, address=1, blocking=False, timeout=1.0):
        """
        Initialize the Pelco D controller.

        - Opens the serial port.
        - Immediately queries the device version for verification.
        - Sets the pan and tilt zero points for calibration.

        Parameters:
          port      : Serial port to use.
          baudrate  : Baud rate.
          address   : Device address.
          blocking  : If True, movement commands will block until the encoder reports
                      that the target position is reached (default: False).
          timeout   : Serial port timeout.
        """
        try:
            self.ser = serial.Serial(
                port=port,
                baudrate=baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=timeout
            )
            print(f"Connected to {port} at {baudrate} baud.")
        except Exception as e:
            print("Error opening serial port:", e)
            self.ser = None
            raise e

        self.address = address
        self.blocking = blocking
        self.rt_feedback_active = False
        self.feedback_thread = None
        self.rt_callback = self._default_rt_callback

        # Home position tracking
        self.home_pan = None
        self.home_tilt = None
        self.abs_positioning_override = True  # Always enabled

        version = self.query_version()
        if version is None:
            print("Error: Failed to retrieve device version. Closing connection.")
            self.close()
            raise Exception("Failed to retrieve device version.")
        else:
            print("Device version:", version)
        
        # Initialize zero points for pan and tilt axes
        print("Setting zero points for pan and tilt axes...")
        self.set_pan_zero_point()
        time.sleep(0.5)  # Give the device time to process
        self.set_tilt_zero_point()
        time.sleep(0.5)  # Give the device time to process
        print("Zero points initialized")

    def set_pan_zero_point(self):
        """Set the pan zero point"""
        cmd = self.create_command(0x00, 0x03, 0x00, 0x67)
        self.send_command(cmd)

    def set_tilt_zero_point(self):
        """Set the tilt zero point"""
        cmd = self.create_command(0x00, 0x03, 0x00, 0x68)
        self.send_command(cmd)

    def _default_rt_callback(self, data):
        print("Real-time feedback:", data)

    def send_command(self, command):
        self.ser.write(command)
        print("Sent:", " ".join(f"{b:02X}" for b in command))

    def create_command(self, cmd1, cmd2, data1, data2):
        checksum = (self.address + cmd1 + cmd2 + data1 + data2) & 0xFF
        return bytearray([0xFF, self.address, cmd1, cmd2, data1, data2, checksum])

    def _read_response(self, expected_length, timeout=1.0):
        start = time.time()
        data = bytearray()
        while time.time() - start < timeout:
            if self.ser.in_waiting:
                data.extend(self.ser.read(self.ser.in_waiting))
            if len(data) >= expected_length:
                break
            time.sleep(0.05)
        return data

    def query_version(self):
        cmd = self.create_command(0xD2, 0x01, 0x00, 0x00)
        self.send_command(cmd)
        time.sleep(0.2)
        response = bytearray()
        start = time.time()
        while time.time() - start < 1.0:
            if self.ser.in_waiting:
                response.extend(self.ser.read(self.ser.in_waiting))
                if response:
                    break
            time.sleep(0.1)
        if response:
            try:
                return response.decode('ascii', errors='replace')
            except Exception:
                return response.hex()
        else:
            return None

    def _feedback_listener(self):
        while self.rt_feedback_active:
            try:
                if self.ser.in_waiting:
                    data = self.ser.read(self.ser.in_waiting)
                    try:
                        decoded_data = data.decode('ascii', errors='replace')
                    except Exception:
                        decoded_data = data.hex()
                    self.rt_callback(decoded_data)
                time.sleep(0.1)
            except Exception as e:
                print("Error in feedback listener:", e)
                break

    def enable_rt_feedback(self):
        self.rt_feedback_active = True
        cmd = self.create_command(0x00, 0x03, 0x00, 0x69)
        self.send_command(cmd)
        self.feedback_thread = threading.Thread(target=self._feedback_listener, daemon=True)
        self.feedback_thread.start()

    def disable_rt_feedback(self):
        self.rt_feedback_active = False
        if self.feedback_thread is not None:
            self.feedback_thread.join(timeout=1)
        cmd = self.create_command(0x00, 0x07, 0x00, 0x69)
        self.send_command(cmd)

    def remote_reset(self):
        cmd = self.create_command(0x00, 0x0F, 0x00, 0x00)
        self.send_command(cmd)

    def factory_default(self):
        cmds = [
            self.create_command(0x00, 0x03, 0x00, 0x5A),
            self.create_command(0x00, 0x07, 0x00, 0x5A),
            self.create_command(0x00, 0x03, 0x00, 0xFF),
            self.create_command(0x00, 0x07, 0x00, 0xFF)
        ]
        for cmd in cmds:
            self.send_command(cmd)
            time.sleep(0.1)

    def close(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
            print("Serial port closed.")


# When run as a script, create an instance with blocking enabled.
if __name__ == '__main__':
    controller = PelcoDController(port='COM3', baudrate=9600, address=1, blocking=True)
