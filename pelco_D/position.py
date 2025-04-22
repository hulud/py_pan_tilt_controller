#!/usr/bin/env python3
import time

class PositionMixin:
    """
    Mixin for position query related functionality
    """
    
    def query_pan_position(self):
        cmd = bytearray([0xFF, self.address, 0x00, 0x51, 0x00, 0x00])
        checksum = (self.address + 0x00 + 0x51 + 0x00 + 0x00) & 0xFF
        cmd.append(checksum)
        self.send_command(cmd)
        time.sleep(0.2)
        response = self._read_response(expected_length=4, timeout=1.0)
        if len(response) == 4:
            if response[0] != 0x59:
                print("Pan query: Unexpected command indicator:", hex(response[0]))
                return None
            p_data = (response[1] << 8) | response[2]
            return p_data / 100.0
        elif len(response) >= 5:
            if response[1] != 0x59:
                print("Pan query: Unexpected command indicator:", hex(response[1]))
                return None
            p_data = (response[2] << 8) | response[3]
            return p_data / 100.0
        else:
            print("Pan query: Incomplete response:", response.hex())
            return None

    def query_tilt_position(self):
        cmd = bytearray([0xFF, self.address, 0x00, 0x53, 0x00, 0x00])
        checksum = (self.address + 0x00 + 0x53 + 0x00 + 0x00) & 0xFF
        cmd.append(checksum)
        self.send_command(cmd)
        time.sleep(0.2)
        response = self._read_response(expected_length=4, timeout=1.0)
        if len(response) == 4:
            if response[0] != 0x5B:
                print("Tilt query: Unexpected command indicator:", hex(response[0]))
                return None
            t_data = (response[1] << 8) | response[2]
        elif len(response) >= 5:
            if response[1] != 0x5B:
                print("Tilt query: Unexpected command indicator:", hex(response[1]))
                return None
            t_data = (response[2] << 8) | response[3]
        else:
            print("Tilt query: Incomplete response:", response.hex())
            return None

        if t_data > 18000:
            return (36000 - t_data) / 100.0
        else:
            return -t_data / 100.0

    def query_position(self):
        pan = self.query_pan_position()
        tilt = self.query_tilt_position()
        return (pan, tilt)
        
    def get_relative_position(self):
        """
        Get position relative to home position.
        Returns (relative_pan, relative_tilt, raw_pan, raw_tilt)
        """
        pan, tilt = self.query_position()
        if pan is None or tilt is None:
            return None, None, pan, tilt
        
        rel_pan = pan
        rel_tilt = tilt
        
        if self.home_pan is not None and self.home_tilt is not None:
            rel_pan = pan - self.home_pan
            rel_tilt = tilt - self.home_tilt
            
        return rel_pan, rel_tilt, pan, tilt

    def set_home_position(self):
        """Set current position as home position"""
        pan, tilt = self.query_position()
        if pan is not None and tilt is not None:
            self.home_pan = pan
            self.home_tilt = tilt
            return True
        return False

    def check_safety_limits(self, direction):
        """
        Check if movement in the given direction would exceed safety limits
        Returns True if movement is safe, False otherwise
        """
        if self.home_pan is None or self.home_tilt is None:
            # No home position set, allow movement
            return True
        
        # Get current position
        pan, tilt = self.query_position()
        if pan is None or tilt is None:
            # Can't determine position, don't allow movement for safety
            return False
        
        # Calculate relative position from home
        rel_pan = pan - self.home_pan
        rel_tilt = tilt - self.home_tilt
        
        # Check limits based on direction
        if direction == 'up' and rel_tilt >= self.safety_limit_degrees:
            return False
        elif direction == 'down' and rel_tilt <= -self.safety_limit_degrees:
            return False
        elif direction == 'left' and rel_pan <= -self.safety_limit_degrees:
            return False
        elif direction == 'right' and rel_pan >= self.safety_limit_degrees:
            return False
        
        return True

    def wait_for_position_settled(self, poll_interval=0.2, stable_time=1.0, tolerance=0.1):
        print("Waiting for position to settle...")
        last_pan, last_tilt = None, None
        stable_start = time.time()
        while True:
            pos = self.query_position()
            if pos[0] is None or pos[1] is None:
                print("Error querying position, retrying...")
                time.sleep(poll_interval)
                continue
            pan, tilt = pos
            if last_pan is not None and last_tilt is not None:
                if abs(pan - last_pan) < tolerance and abs(tilt - last_tilt) < tolerance:
                    if time.time() - stable_start >= stable_time:
                        print(f"Position settled: Pan = {pan}°, Tilt = {tilt}°")
                        break
                else:
                    stable_start = time.time()
            else:
                stable_start = time.time()
            last_pan, last_tilt = pan, tilt
            time.sleep(poll_interval)
