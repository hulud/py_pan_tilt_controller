#!/usr/bin/env python3
"""
Pelco D Protocol Device Simulator

Simulates a pan-tilt device that follows the Pelco D protocol,
maintaining internal state and responding correctly to commands.
"""

import time
import threading
import math
import logging

logger = logging.getLogger(__name__)

class PelcoDSimulator:
    """
    Simulator for a Pelco D protocol pan-tilt device
    
    This class implements the same interface as PelcoDController but simulates
    device behavior instead of communicating with actual hardware.
    """
    
    def __init__(self, address=1):
        """
        Initialize the simulator
        
        Args:
            address: Device address (1-255)
        """
        self.address = address
        
        # Position state
        self._pan_pos = 180.0  # Default 180 degrees (center)
        self._tilt_pos = 0.0   # Default 0 degrees (level)
        self._target_pan = self._pan_pos
        self._target_tilt = self._tilt_pos
        
        # Movement parameters
        self._pan_speed = 0
        self._tilt_speed = 0
        self._max_pan_speed = 20.0  # degrees per second
        self._max_tilt_speed = 15.0  # degrees per second
        
        # Home position and safety features
        self.home_pan = None
        self.home_tilt = None
        self.safety_limit_degrees = 45.0
        self.abs_positioning_override = False
        
        # Presets storage (preset_id -> (pan, tilt))
        self.presets = {}
        
        # Movement simulation thread
        self._stop_thread = False
        self._movement_thread = threading.Thread(target=self._movement_simulation, daemon=True)
        self._movement_thread.start()
        
        logger.info(f"Initialized Pelco D simulator with address {address}")
    
    def _movement_simulation(self):
        """Background thread that simulates device movement"""
        last_time = time.time()
        
        while not self._stop_thread:
            # Calculate time delta
            current_time = time.time()
            delta_time = current_time - last_time
            last_time = current_time
            
            # Check if we need to enforce safety limits
            if self.home_pan is not None and self.home_tilt is not None:
                rel_pan, rel_tilt, _, _ = self.get_relative_position()
                
                # If we're about to exceed a safety limit, stop the movement
                if (self._pan_speed > 0 and rel_pan >= self.safety_limit_degrees) or \
                   (self._pan_speed < 0 and rel_pan <= -self.safety_limit_degrees):
                    self._pan_speed = 0
                
                if (self._tilt_speed > 0 and rel_tilt >= self.safety_limit_degrees) or \
                   (self._tilt_speed < 0 and rel_tilt <= -self.safety_limit_degrees):
                    self._tilt_speed = 0
            
            # Update pan position based on speed and time
            if self._pan_speed != 0:
                speed_factor = abs(self._pan_speed) / 0x3F  # Normalize to 0-1
                change = speed_factor * self._max_pan_speed * delta_time
                
                # Determine direction
                if self._pan_speed > 0:
                    self._pan_pos += change
                else:
                    self._pan_pos -= change
                
                # Normalize to 0-360
                self._pan_pos = self._pan_pos % 360
            
            # Update tilt position based on speed and time
            if self._tilt_speed != 0:
                speed_factor = abs(self._tilt_speed) / 0x3F  # Normalize to 0-1
                change = speed_factor * self._max_tilt_speed * delta_time
                
                # Determine direction
                if self._tilt_speed > 0:
                    self._tilt_pos += change
                else:
                    self._tilt_pos -= change
                
                # Clamp to -90 to +90
                self._tilt_pos = max(-90, min(90, self._tilt_pos))
            
            # Check if we've reached target positions for absolute movement
            if abs(self._pan_pos - self._target_pan) < 0.1:
                self._pan_pos = self._target_pan
                
            if abs(self._tilt_pos - self._target_tilt) < 0.1:
                self._tilt_pos = self._target_tilt
            
            # Small sleep to prevent CPU hogging
            time.sleep(0.01)
    
    def close(self):
        """Clean up resources"""
        self._stop_thread = True
        if self._movement_thread.is_alive():
            self._movement_thread.join(timeout=1)
        logger.info("Simulator closed")
    
    # Basic movement commands
    
    def move_up(self, speed=0x20):
        """Move up at the specified speed"""
        # Check if movement is within safety limits
        if self.home_tilt is not None:
            rel_pan, rel_tilt, _, _ = self.get_relative_position()
            if rel_tilt >= self.safety_limit_degrees:
                logger.warning("Cannot move up: safety limit reached")
                return
        
        self._tilt_speed = abs(speed)
        logger.debug(f"Moving up at speed {speed}")
    
    def move_down(self, speed=0x20):
        """Move down at the specified speed"""
        # Check if movement is within safety limits
        if self.home_tilt is not None:
            rel_pan, rel_tilt, _, _ = self.get_relative_position()
            if rel_tilt <= -self.safety_limit_degrees:
                logger.warning("Cannot move down: safety limit reached")
                return
                
        self._tilt_speed = -abs(speed)
        logger.debug(f"Moving down at speed {speed}")
    
    def move_left(self, speed=0x20):
        """Move left at the specified speed"""
        # Check if movement is within safety limits
        if self.home_pan is not None:
            rel_pan, rel_tilt, _, _ = self.get_relative_position()
            if rel_pan <= -self.safety_limit_degrees:
                logger.warning("Cannot move left: safety limit reached")
                return
                
        self._pan_speed = -abs(speed)
        logger.debug(f"Moving left at speed {speed}")
    
    def move_right(self, speed=0x20):
        """Move right at the specified speed"""
        # Check if movement is within safety limits
        if self.home_pan is not None:
            rel_pan, rel_tilt, _, _ = self.get_relative_position()
            if rel_pan >= self.safety_limit_degrees:
                logger.warning("Cannot move right: safety limit reached")
                return
                
        self._pan_speed = abs(speed)
        logger.debug(f"Moving right at speed {speed}")
    
    def move_left_up(self, pan_speed=0x20, tilt_speed=0x20):
        """Move left and up at the specified speeds"""
        # Check safety limits separately for each axis
        within_limits = True
        
        if self.home_pan is not None and self.home_tilt is not None:
            rel_pan, rel_tilt, _, _ = self.get_relative_position()
            if rel_pan <= -self.safety_limit_degrees:
                logger.warning("Cannot move left: safety limit reached")
                within_limits = False
            
            if rel_tilt >= self.safety_limit_degrees:
                logger.warning("Cannot move up: safety limit reached")
                within_limits = False
        
        if within_limits:
            self._pan_speed = -abs(pan_speed)
            self._tilt_speed = abs(tilt_speed)
            logger.debug(f"Moving left-up at speeds {pan_speed}, {tilt_speed}")
    
    def move_left_down(self, pan_speed=0x20, tilt_speed=0x20):
        """Move left and down at the specified speeds"""
        # Check safety limits separately for each axis
        within_limits = True
        
        if self.home_pan is not None and self.home_tilt is not None:
            rel_pan, rel_tilt, _, _ = self.get_relative_position()
            if rel_pan <= -self.safety_limit_degrees:
                logger.warning("Cannot move left: safety limit reached")
                within_limits = False
            
            if rel_tilt <= -self.safety_limit_degrees:
                logger.warning("Cannot move down: safety limit reached")
                within_limits = False
        
        if within_limits:
            self._pan_speed = -abs(pan_speed)
            self._tilt_speed = -abs(tilt_speed)
            logger.debug(f"Moving left-down at speeds {pan_speed}, {tilt_speed}")
    
    def move_right_up(self, pan_speed=0x20, tilt_speed=0x20):
        """Move right and up at the specified speeds"""
        # Check safety limits separately for each axis
        within_limits = True
        
        if self.home_pan is not None and self.home_tilt is not None:
            rel_pan, rel_tilt, _, _ = self.get_relative_position()
            if rel_pan >= self.safety_limit_degrees:
                logger.warning("Cannot move right: safety limit reached")
                within_limits = False
            
            if rel_tilt >= self.safety_limit_degrees:
                logger.warning("Cannot move up: safety limit reached")
                within_limits = False
        
        if within_limits:
            self._pan_speed = abs(pan_speed)
            self._tilt_speed = abs(tilt_speed)
            logger.debug(f"Moving right-up at speeds {pan_speed}, {tilt_speed}")
    
    def move_right_down(self, pan_speed=0x20, tilt_speed=0x20):
        """Move right and down at the specified speeds"""
        # Check safety limits separately for each axis
        within_limits = True
        
        if self.home_pan is not None and self.home_tilt is not None:
            rel_pan, rel_tilt, _, _ = self.get_relative_position()
            if rel_pan >= self.safety_limit_degrees:
                logger.warning("Cannot move right: safety limit reached")
                within_limits = False
            
            if rel_tilt <= -self.safety_limit_degrees:
                logger.warning("Cannot move down: safety limit reached")
                within_limits = False
        
        if within_limits:
            self._pan_speed = abs(pan_speed)
            self._tilt_speed = -abs(tilt_speed)
            logger.debug(f"Moving right-down at speeds {pan_speed}, {tilt_speed}")
    
    def stop(self):
        """Stop all movement"""
        self._pan_speed = 0
        self._tilt_speed = 0
        logger.debug("Movement stopped")
    
    # Position querying
    
    def query_pan_position(self):
        """Query the current pan position in degrees"""
        return self._pan_pos
    
    def query_tilt_position(self):
        """Query the current tilt position in degrees"""
        return self._tilt_pos
    
    def query_position(self):
        """Query both pan and tilt positions"""
        return (self._pan_pos, self._tilt_pos)
    
    def get_relative_position(self):
        """
        Get position relative to home position
        
        Returns:
            Tuple of (rel_pan, rel_tilt, raw_pan, raw_tilt)
        """
        raw_pan = self._pan_pos
        raw_tilt = self._tilt_pos
        
        # Calculate relative position if home is set
        if self.home_pan is not None and self.home_tilt is not None:
            # Calculate relative pan (shortest path)
            rel_pan = raw_pan - self.home_pan
            if rel_pan > 180:
                rel_pan -= 360
            elif rel_pan < -180:
                rel_pan += 360
                
            # Calculate relative tilt
            rel_tilt = raw_tilt - self.home_tilt
        else:
            rel_pan = None
            rel_tilt = None
        
        return (rel_pan, rel_tilt, raw_pan, raw_tilt)
    
    def wait_for_position_settled(self, poll_interval=0.2, stable_time=1.0, tolerance=0.1):
        """Wait for position to stabilize"""
        if self._pan_speed == 0 and self._tilt_speed == 0:
            return True
        
        # Wait for movement to stop
        start_wait = time.time()
        last_pos = self.query_position()
        
        while time.time() - start_wait < stable_time:
            time.sleep(poll_interval)
            current_pos = self.query_position()
            
            # Check if position changed within tolerance
            pan_diff = abs(current_pos[0] - last_pos[0])
            tilt_diff = abs(current_pos[1] - last_pos[1])
            
            if pan_diff > tolerance or tilt_diff > tolerance:
                # Position changed, reset timer
                start_wait = time.time()
                last_pos = current_pos
        
        return True
    
    # Home position and safety
    
    def set_home_position(self):
        """Set current position as home position"""
        self.home_pan, self.home_tilt = self.query_position()
        logger.info(f"Home position set to pan={self.home_pan}, tilt={self.home_tilt}")
        return True
    
    def check_safety_limits(self, direction):
        """
        Check if movement in a direction is safe
        
        Args:
            direction: One of 'up', 'down', 'left', 'right'
            
        Returns:
            True if movement is safe, False otherwise
        """
        if self.home_pan is None or self.home_tilt is None:
            # No home position set, consider all movement safe
            return True
        
        rel_pan, rel_tilt, _, _ = self.get_relative_position()
        
        if direction == 'up' and rel_tilt > self.safety_limit_degrees:
            return False
        elif direction == 'down' and rel_tilt < -self.safety_limit_degrees:
            return False
        elif direction == 'left' and rel_pan < -self.safety_limit_degrees:
            return False
        elif direction == 'right' and rel_pan > self.safety_limit_degrees:
            return False
        
        return True
    
    # Absolute positioning
    
    def set_abs_positioning_override(self, enable):
        """Enable or disable absolute positioning override"""
        self.abs_positioning_override = enable
        logger.info(f"Absolute positioning override set to {enable}")
    
    def absolute_pan(self, angle):
        """
        Move to absolute pan position
        
        Args:
            angle: Pan angle in degrees (0-360)
        """
        if not self.abs_positioning_override:
            logger.warning("Absolute positioning is disabled")
            return
        
        # Check safety limits for absolute movement
        if self.home_pan is not None:
            # Calculate what the relative position would be after movement
            target_angle = angle % 360
            rel_angle = target_angle - self.home_pan
            
            # Normalize to -180 to 180
            if rel_angle > 180:
                rel_angle -= 360
            elif rel_angle < -180:
                rel_angle += 360
                
            if abs(rel_angle) > self.safety_limit_degrees:
                logger.warning(f"Absolute pan position {angle}° exceeds safety limit")
                return
        
        self._target_pan = angle % 360
        
        # Calculate shortest path
        current = self._pan_pos
        target = self._target_pan
        diff = target - current
        
        if abs(diff) > 180:
            # Take the shorter path
            if diff > 0:
                self._pan_speed = -0x20  # Move left
            else:
                self._pan_speed = 0x20   # Move right
        else:
            if diff > 0:
                self._pan_speed = 0x20   # Move right
            else:
                self._pan_speed = -0x20  # Move left
        
        logger.debug(f"Moving to absolute pan: {angle}")
    
    def absolute_tilt(self, angle):
        """
        Move to absolute tilt position
        
        Args:
            angle: Tilt angle in degrees (-90 to +90)
        """
        if not self.abs_positioning_override:
            logger.warning("Absolute positioning is disabled")
            return
        
        # Check safety limits for absolute movement
        if self.home_tilt is not None:
            # Calculate what the relative position would be after movement
            rel_angle = angle - self.home_tilt
            
            if abs(rel_angle) > self.safety_limit_degrees:
                logger.warning(f"Absolute tilt position {angle}° exceeds safety limit")
                return
        
        self._target_tilt = max(-90, min(90, angle))
        
        # Determine direction
        diff = self._target_tilt - self._tilt_pos
        if diff > 0:
            self._tilt_speed = 0x20   # Move up
        else:
            self._tilt_speed = -0x20  # Move down
        
        logger.debug(f"Moving to absolute tilt: {angle}")
    
    # Presets
    
    def set_preset(self, preset_id):
        """Store current position as a preset"""
        self.presets[preset_id] = self.query_position()
        logger.info(f"Set preset {preset_id} at position {self.presets[preset_id]}")
    
    def call_preset(self, preset_id):
        """Move to a preset position"""
        if preset_id not in self.presets:
            logger.warning(f"Preset {preset_id} not found")
            return
        
        pan, tilt = self.presets[preset_id]
        
        # Enable absolute positioning temporarily
        old_override = self.abs_positioning_override
        self.abs_positioning_override = True
        
        # Move to preset position
        self.absolute_pan(pan)
        self.absolute_tilt(tilt)
        
        # Restore override setting
        self.abs_positioning_override = old_override
        
        logger.info(f"Called preset {preset_id} at position {self.presets[preset_id]}")
    
    def delete_preset(self, preset_id):
        """Delete a preset position"""
        if preset_id in self.presets:
            del self.presets[preset_id]
            logger.info(f"Deleted preset {preset_id}")
        else:
            logger.warning(f"Preset {preset_id} not found")
    
    # Optical controls (stubs for compatibility)
    
    def zoom_in(self):
        """Simulate zoom in"""
        logger.info("Zoom in (simulated)")
    
    def zoom_out(self):
        """Simulate zoom out"""
        logger.info("Zoom out (simulated)")
    
    def focus_far(self):
        """Simulate focus far"""
        logger.info("Focus far (simulated)")
    
    def focus_near(self):
        """Simulate focus near"""
        logger.info("Focus near (simulated)")
    
    def iris_open(self):
        """Simulate iris open"""
        logger.info("Iris open (simulated)")
    
    def iris_shut(self):
        """Simulate iris shut"""
        logger.info("Iris shut (simulated)")
    
    # Auxiliary functions (stubs for compatibility)
    
    def open_aux(self, aux_value=1):
        """Simulate opening auxiliary device"""
        logger.info(f"Open auxiliary {aux_value} (simulated)")
    
    def shut_aux(self, aux_value=1):
        """Simulate closing auxiliary device"""
        logger.info(f"Close auxiliary {aux_value} (simulated)")
    
    # Advanced features (stubs for compatibility)
    
    def start_cruise(self):
        """Simulate starting cruise mode"""
        logger.info("Start cruise (simulated)")
    
    def set_cruise_dwell_time(self, time_value):
        """Simulate setting cruise dwell time"""
        logger.info(f"Set cruise dwell time to {time_value} (simulated)")
    
    def set_cruise_speed(self, speed_value):
        """Simulate setting cruise speed"""
        logger.info(f"Set cruise speed to {speed_value} (simulated)")
    
    # System functions
    
    def remote_reset(self):
        """Simulate remote reset"""
        logger.info("Remote reset (simulated)")
        self._pan_pos = 180.0
        self._tilt_pos = 0.0
        self._pan_speed = 0
        self._tilt_speed = 0
    
    def factory_default(self):
        """Simulate factory reset"""
        logger.info("Factory default (simulated)")
        self._pan_pos = 180.0
        self._tilt_pos = 0.0
        self._pan_speed = 0
        self._tilt_speed = 0
        self.home_pan = None
        self.home_tilt = None
        self.presets.clear()
