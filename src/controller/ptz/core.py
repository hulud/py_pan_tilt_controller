"""
src/controller/ptz/core.py

High-level PTZ controller - using protocol's parse_response
(works with the original PelcoDProtocol names)

Public import path stays:
    from src.controller.ptz import PTZController
"""
from __future__ import annotations
import logging
from typing import Dict, Any, Tuple

from src.connection import ConnectionBase, SerialConnection
from src.protocol import PelcoDProtocol
import time
log = logging.getLogger(__name__)


class PTZController:
    # ------------------------------------------------------------------ init
    def __init__(self, connection_config: Dict[str, Any], address: int = 1) -> None:
        self.connection: ConnectionBase = self._create_connection(connection_config)
        self.protocol = PelcoDProtocol(address=address)

        # --- tiny shims so we work with either protocol API name -----
        self._build_pan_query = (
            getattr(self.protocol, "pan_position_query", None)
            or getattr(self.protocol, "query_pan_position")
        )
        self._build_tilt_query = (
            getattr(self.protocol, "tilt_position_query", None)
            or getattr(self.protocol, "query_tilt_position")
        )

        # --------------------------------------------------------------
        if not self.connection.open():
            raise ConnectionError("Failed to open serial connection")

        # flush any pending bytes; ignore timeout
        try:
            self.connection.receive(size=64, timeout=0.1)
        except Exception:
            pass

        self.set_home_position()
    # --------------------------------------------------------- private utils
    def _create_connection(self, cfg: Dict[str, Any]) -> ConnectionBase:
        port = cfg.get("port", "COM3")
        
        # If simulator is explicitly requested
        if port == "SIMULATOR":
            log.info("Using simulator connection (explicit configuration)")
            from src.connection import SimulatorConnection
            return SimulatorConnection()
            
        # Try to create a serial connection first
        log.info(f"Using serial connection on port {port}")
        try:
            serial_conn = SerialConnection(
                port=port,
                baudrate=cfg.get("baudrate", 9600),
                data_bits=cfg.get("data_bits", 8),
                stop_bits=cfg.get("stop_bits", 1),
                parity=cfg.get("parity", "N"),
                polling_rate=cfg.get("polling_rate"),
                enable_polling=cfg.get("enable_polling", True),
            )
            
            # Test if we can actually open the port
            if serial_conn.open():
                log.info(f"Successfully opened serial connection on {port}")
                serial_conn.close()  # Close it so __init__ can open it cleanly
                return serial_conn
            else:
                log.warning(f"Failed to open serial connection on {port}")
        except Exception as e:
            log.error(f"Error creating serial connection: {e}")

    def _send_command(self, frame: bytes) -> None:
        self.connection.send(frame)

    # ------------------------------------------------------------- RX logic
    def _read(self, timeout: float = 2.0) -> bytes:
        """
        Read response from the device. Handles both standard 7-byte format and
        BIT-CCTV's custom 5-byte format. Never raises on incomplete or malformed frames;
        only emits warnings and returns whatever was received.
        """
        try:
            buffer = bytearray()
            initial_read_size = 1

            # Step 1: initial read
            try:
                chunk = self.connection.receive(size=initial_read_size, timeout=timeout)
                if not chunk:
                    print("WARNING: No data received within timeout period")
                    return bytes()
                buffer.extend(chunk)
            except TimeoutError:
                print("WARNING: Timeout during initial read")
                return bytes()
            except Exception as e:
                print(f"WARNING: Exception during initial data receive: {e}")
                return bytes()

            # Step 2: determine expected length
            expected_len = 7 if buffer[0] == 0xFF else 5
            remain = expected_len - len(buffer)

            # Step 3: read remainder
            while remain > 0:
                try:
                    chunk = self.connection.receive(size=remain, timeout=timeout)
                    if not chunk:
                        print(f"WARNING: No data received within timeout period ({timeout}s)")
                        break
                    buffer.extend(chunk)
                    remain = expected_len - len(buffer)
                except TimeoutError:
                    print(f"WARNING: Timeout after receiving {len(buffer)} bytes: {' '.join(f'{b:02X}' for b in buffer)}")
                    break
                except Exception as e:
                    print(f"WARNING: Exception during data receive: {e}")
                    break

            if len(buffer) != expected_len:
                print(f"WARNING: Expected {expected_len} bytes, got {len(buffer)}")

            # validation warnings only
            if len(buffer) == 5:
                try:
                    if buffer[1] not in (0x59, 0x5B):
                        print(f"WARNING: Invalid command byte {buffer[1]:02X}, expected 59 or 5B")
                except Exception as e:
                    print(f"WARNING: Exception during 5-byte message validation: {e}")
            elif len(buffer) == 7:
                try:
                    if buffer[0] != 0xFF:
                        print(f"WARNING: Invalid sync byte {buffer[0]:02X}, expected FF")
                    if buffer[1] != self.protocol.address:
                        print(f"WARNING: Invalid address {buffer[1]:02X}, expected {self.protocol.address:02X}")
                    if buffer[2] != 0x00:
                        print(f"WARNING: Invalid command byte1 {buffer[2]:02X}, expected 00")
                    if buffer[3] not in (0x59, 0x5B):
                        print(f"WARNING: Invalid command byte2 {buffer[3]:02X}, expected 59 or 5B")
                except Exception as e:
                    print(f"WARNING: Exception during 7-byte message validation: {e}")

            return bytes(buffer)
        except Exception as e:
            print(f"WARNING: Unexpected error in _read method: {e}")
            return bytes()

    # --------------------------------------------------- position utilities

    def query_pan_position(self) -> float:
        """
        Query the current pan position.

        Returns:
            The angle in degrees.

        Notes:
            On any error or malformed response, this will print a warning
            and return 0.0 instead of raising.
        """
        try:
            frame = self._build_pan_query()
            self._send_command(frame)
            raw_response = self._read()  # May be shorter than expected; only warns
            result = self.protocol.parse_response(raw_response)
            if not result or result.get('type') != 'pan_position' or not result.get('valid'):
                print(f"WARNING: Invalid pan position response: {raw_response.hex()}")
                return 0.0
            return result['angle']
        except Exception as e:
            print(f"WARNING: Error querying pan position: {e}")
            return 0.0

    def query_tilt_position(self) -> float:
        """
        Query the current tilt position.

        Returns:
            The angle in degrees.

        Notes:
            On any error or malformed response, this will print a warning
            and return 0.0 instead of raising.
        """
        try:
            frame = self._build_tilt_query()
            self._send_command(frame)
            raw_response = self._read()
            result = self.protocol.parse_response(raw_response)
            if not result or result.get('type') != 'tilt_position' or not result.get('valid'):
                print(f"WARNING: Invalid tilt position response: {raw_response.hex()}")
                return 0.0
            return result['angle']
        except Exception as e:
            print(f"WARNING: Error querying tilt position: {e}")
            return 0.0

    def get_relative_position(self) -> Tuple[float, float, dict]:
        """
        Get the current pan and tilt position relative to the stored zero points.

        Returns:
            rel_pan_ang  (float): pan angle in degrees minus zero_pan_angle
            rel_tilt_ang (float): tilt angle in degrees minus zero_tilt_angle
            status       (dict): {
                'pan_valid': bool,   # True if pan_angle != 0.0
                'tilt_valid': bool   # True if tilt_angle != 0.0
            }
        """
        # 1) Query absolute angles
        pan_angle = self.query_pan_position()
        tilt_angle = self.query_tilt_position()

        # 2) Load zero‐angle offsets (default to 0.0 if not set)
        zero_pan_ang = getattr(self, '_zero_pan_angle', 0.0)
        zero_tilt_ang = getattr(self, '_zero_tilt_angle', 0.0)

        # 3) Compute relative angles
        rel_pan_ang = pan_angle - zero_pan_ang
        rel_tilt_ang = tilt_angle - zero_tilt_ang

        # 4) Build validity flags
        status = {
            'pan_valid': pan_angle != 0.0,
            'tilt_valid': tilt_angle != 0.0,
        }

        return rel_pan_ang, rel_tilt_ang, status

    def set_home_position(self):
        """
        Initialize zero points:
          1) Save current absolute pan/tilt as software zero references
          2) Delegate to hardware zero-point routine
        """

        try:
            log.info("Zeroing pan…")
            self._send_command(self.protocol.set_pan_zero_point())
            time.sleep(0.2)
            log.info("Zeroing tilt…")
            self._send_command(self.protocol.set_tilt_zero_point())
            time.sleep(0.2)
        except Exception as e:
            log.warning(f"Error sending zero‐point commands: {e}")


        pan_ang = self.query_pan_position()
        tilt_ang = self.query_tilt_position()

        self._zero_pan_angle = pan_ang
        self._zero_tilt_angle = tilt_ang



    def stop(self):
        """Stop all movement."""
        command = self.protocol.stop()
        self._send_command(command)

    def move_up(self, speed=0x10):
        """
        Move the camera up at the specified speed.

        Args:
            speed: Movement speed (0x00-0x3F)
        """
        command = self.protocol.move_up(speed)
        self._send_command(command)

    def move_down(self, speed=0x10):
        """
        Move the camera down at the specified speed.

        Args:
            speed: Movement speed (0x00-0x3F)
        """
        command = self.protocol.move_down(speed)
        self._send_command(command)

    def move_left(self, speed=0x10):
        """
        Move the camera left at the specified speed.

        Args:
            speed: Movement speed (0x00-0x3F)
        """
        command = self.protocol.move_left(speed)
        self._send_command(command)

    def move_right(self, speed=0x10):
        """
        Move the camera right at the specified speed.

        Args:
            speed: Movement speed (0x00-0x3F)
        """
        command = self.protocol.move_right(speed)
        self._send_command(command)

    def absolute_pan(self, angle):
        """
        Move to an absolute pan position.

        Args:
            angle: Pan angle in degrees (0-360)
        """
        command = self.protocol.absolute_pan(angle)
        self._send_command(command)

    def absolute_tilt(self, angle):
        """
        Move to an absolute tilt position.

        Args:
            angle: Tilt angle in degrees (-90 to +90)
        """
        command = self.protocol.absolute_tilt(angle)
        self._send_command(command)

    def query_position(self):
        """
        Query the current position.
        Returns:
            Tuple of (pan_angle, tilt_angle) in degrees
        """
        pan_angle = self.query_pan_position()
        tilt_angle = self.query_tilt_position()
        return (pan_angle, tilt_angle)

    # Basic implementations for other methods referenced in the API routes
    def set_preset(self, preset_id):
        """Set a preset position."""
        command = self.protocol.set_preset(preset_id)
        self._send_command(command)

    def call_preset(self, preset_id):
        """Call a preset position."""
        command = self.protocol.call_preset(preset_id)
        self._send_command(command)

    def clear_preset(self, preset_id):
        """Clear a preset position."""
        command = self.protocol.clear_preset(preset_id)
        self._send_command(command)

    def zoom_in(self):
        """Zoom in."""
        command = self.protocol.zoom_in()
        self._send_command(command)

    def zoom_out(self):
        """Zoom out."""
        command = self.protocol.zoom_out()
        self._send_command(command)

    def focus_far(self):
        """Focus far."""
        command = self.protocol.focus_far()
        self._send_command(command)

    def focus_near(self):
        """Focus near."""
        command = self.protocol.focus_near()
        self._send_command(command)

    def iris_open(self):
        """Open iris."""
        command = self.protocol.iris_open()
        self._send_command(command)

    def iris_close(self):
        """Close iris."""
        command = self.protocol.iris_close()
        self._send_command(command)

    def aux_on(self, aux_id):
        """Turn on auxiliary device."""
        command = self.protocol.aux_on(aux_id)
        self._send_command(command)

    def aux_off(self, aux_id):
        """Turn off auxiliary device."""
        command = self.protocol.aux_off(aux_id)
        self._send_command(command)

    def remote_reset(self):
        """Reset the device."""
        command = self.protocol.remote_reset()
        self._send_command(command)

    @property
    def connection_type(self):
        """Get the connection type."""
        return self.connection.__class__.__name__

    def close(self) -> None:
        log.info("Closing connection")
        try:
            self.connection.close()
            # Give the OS time to fully release the port
            import time
            time.sleep(0.5)
        except Exception as e:
            log.error(f"Error during connection close: {e}")
            # Continue with cleanup even if error occurs

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
