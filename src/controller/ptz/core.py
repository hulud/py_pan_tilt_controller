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

        self.init_zero_points()
    # --------------------------------------------------------- private utils
    def _create_connection(self, cfg: Dict[str, Any]) -> ConnectionBase:
        port = cfg.get("port", "COM3")
        if port == "SIMULATOR":
            log.info("Using simulator connection")
            from src.connection import SimulatorConnection
            return SimulatorConnection()
        else:
            log.info(f"Using serial connection on port {port}")
            return SerialConnection(
                port=port,
                baudrate=cfg.get("baudrate", 9600),
                data_bits=cfg.get("data_bits", 8),
                stop_bits=cfg.get("stop_bits", 1),
                parity=cfg.get("parity", "N"),
            )

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

    def query_tilt_position(self) -> Tuple[int, float]:
        """
        Query the current tilt position.

        Returns:
            Tuple of (raw_value, angle_in_degrees)

        Notes:
            On any error or malformed response, this will print a warning
            and return (0, 0.0) instead of raising.
        """
        try:
            frame = self._build_tilt_query()
            self._send_command(frame)
            raw_response = self._read()
            result = self.protocol.parse_response(raw_response)
            if not result or result.get('type') != 'tilt_position' or not result.get('valid'):
                print(f"WARNING: Invalid tilt position response: {raw_response.hex()}")
                return 0, 0.0
            return result['raw'], result['angle']
        except Exception as e:
            print(f"WARNING: Error querying tilt position: {e}")
            return 0, 0.0

    def get_relative_position(self):
        """
        Get the current pan and tilt position with status information.
        Returns:
            Tuple of (rel_pan, rel_tilt, rel_raw_pan, rel_raw_tilt, status)
        """
        # Query absolute positions
        pan_angle = self.query_pan_position()
        raw_tilt_value, tilt_angle = self.query_tilt_position()
        raw_pan_value = pan_angle

        status = {
            'pan_valid': pan_angle != 0.0,
            'tilt_valid': raw_tilt_value != 0 or tilt_angle != 0.0,
        }

        # Compute relative values against saved zero-points
        zero_raw_pan = getattr(self, '_zero_raw_pan', 0)
        zero_raw_tilt = getattr(self, '_zero_raw_tilt', 0)
        zero_pan_ang = getattr(self, '_zero_pan_angle', 0.0)
        zero_tilt_ang = getattr(self, '_zero_tilt_angle', 0.0)

        rel_raw_pan = raw_pan_value - zero_raw_pan
        rel_raw_tilt = raw_tilt_value - zero_raw_tilt
        rel_pan_ang = pan_angle - zero_pan_ang
        rel_tilt_ang = tilt_angle - zero_tilt_ang

        return rel_pan_ang, rel_tilt_ang, rel_raw_pan, rel_raw_tilt, status

    def init_zero_points(self):
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
        raw_tilt, tilt_ang = self.query_tilt_position()

        self._zero_raw_pan = pan_ang
        self._zero_raw_tilt = raw_tilt
        self._zero_pan_angle = pan_ang
        self._zero_tilt_angle = tilt_ang



    def stop(self):
        """Stop all movement."""
        command = self.protocol.stop()
        self._send_command(command)

    # ... rest of movement & preset methods unchanged ...

    def query_position(self):
        """
        Query the current position.
        Returns:
            Tuple of (pan_angle, tilt_angle) in degrees
        """
        pan_angle = self.query_pan_position()
        _, tilt_angle = self.query_tilt_position()
        return (pan_angle, tilt_angle)

    # ... remaining methods unchanged ...

    @property
    def connection_type(self):
        """Get the connection type."""
        return self.connection.__class__.__name__

    def close(self) -> None:
        log.info("Closing connection")
        self.connection.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
