#!/usr/bin/env python3
import time

class AbsolutePositionMixin:
    """
    Mixin for absolute positioning functionality
    """
    
    def absolute_pan(self, angle):
        """
        Move to an absolute pan position.
        For angles < 0, converts to the equivalent positive value (e.g. -5° becomes 355°).
        If blocking is enabled, this method waits until the encoder reports the target.
        """
        if not self.abs_positioning_override:
            print("Absolute positioning is disabled for safety. Use set_abs_positioning_override(True) to enable.")
            return
            
        if angle < 0:
            value = 36000 - int(abs(angle) * 100)
        else:
            value = int(angle * 100)
        data1 = (value >> 8) & 0xFF
        data2 = value & 0xFF
        cmd = self.create_command(0x00, 0x4B, data1, data2)
        self.send_command(cmd)
        if self.blocking:
            self._wait_for_pan(angle, tolerance=0.2, max_wait=5.0)

    def absolute_tilt(self, angle):
        """
        Move to an absolute tilt position.
        For negative angles: value = abs(angle) * 100.
        For positive angles: value = 36000 - int(angle * 100).
        If blocking is enabled, this method waits until the encoder reports the target.
        """
        if not self.abs_positioning_override:
            print("Absolute positioning is disabled for safety. Use set_abs_positioning_override(True) to enable.")
            return
            
        if angle < 0:
            value = int(abs(angle) * 100)
        else:
            value = 36000 - int(angle * 100)
        data1 = (value >> 8) & 0xFF
        data2 = value & 0xFF
        cmd = self.create_command(0x00, 0x4D, data1, data2)
        self.send_command(cmd)
        if self.blocking:
            self._wait_for_tilt(angle, tolerance=0.2, max_wait=5.0)
            
    def set_abs_positioning_override(self, override):
        """Enable or disable absolute positioning override"""
        self.abs_positioning_override = override
        if override:
            print("WARNING: Absolute positioning override enabled. Use caution with tilt values!")

    def _wait_for_pan(self, angle, tolerance=0.2, max_wait=5.0):
        """
        Block until the pan encoder reading is within tolerance of the target.
        Converts a negative angle to its equivalent positive value.
        """
        target = angle if angle >= 0 else 360 + angle
        start_time = time.time()
        current_pan = None
        while time.time() - start_time < max_wait:
            current_pan = self.query_pan_position()
            if current_pan is not None:
                diff = abs(current_pan - target)
                if diff > 180:
                    diff = 360 - diff
                if diff <= tolerance:
                    print(f"Blocking: reached pan {current_pan:.2f}° (target {target}°)")
                    return current_pan
            time.sleep(0.05)
        print(f"Blocking timeout: pan did not reach {target}° within {max_wait} seconds.")
        return current_pan

    def _wait_for_tilt(self, angle, tolerance=0.2, max_wait=5.0):
        """
        Block until the tilt encoder reading is within tolerance of the target.
        """
        start_time = time.time()
        current_tilt = None
        while time.time() - start_time < max_wait:
            current_tilt = self.query_tilt_position()
            if current_tilt is not None:
                if abs(current_tilt - angle) <= tolerance:
                    print(f"Blocking: reached tilt {current_tilt:.2f}° (target {angle}°)")
                    return current_tilt
            time.sleep(0.05)
        print(f"Blocking timeout: tilt did not reach {angle}° within {max_wait} seconds.")
        return current_tilt
