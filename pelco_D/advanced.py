#!/usr/bin/env python3
import time

class AdvancedMixin:
    """
    Mixin for advanced control functionality including cruise and line scan
    """
    
    # =============================
    #      Cruising Functions
    # =============================
    def start_cruise(self):
        cmd = self.create_command(0x00, 0x07, 0x00, 0x62)
        self.send_command(cmd)

    def set_cruise_dwell_time(self, dwell_time):
        cmd = self.create_command(0x00, 0x03, 0x00, dwell_time)
        self.send_command(cmd)

    def set_cruise_speed(self, speed):
        cmd = self.create_command(0x00, 0x03, 0x00, speed)
        self.send_command(cmd)

    # =============================
    #      Line Scan Functions
    # =============================
    def set_line_scan_start(self):
        cmd = self.create_command(0x00, 0x03, 0x00, 0x5C)
        self.send_command(cmd)

    def set_line_scan_end(self):
        cmd = self.create_command(0x00, 0x03, 0x00, 0x5D)
        self.send_command(cmd)

    def run_line_scan(self):
        cmd = self.create_command(0x00, 0x07, 0x00, 0x63)
        self.send_command(cmd)

    def set_line_scan_speed(self, speed):
        cmd = self.create_command(0x00, 0x03, 0x00, speed)
        self.send_command(cmd)

    # =============================
    #      Guard Location
    # =============================
    def enable_guard(self):
        cmd = self.create_command(0x00, 0x03, 0x00, 0x5E)
        self.send_command(cmd)

    def disable_guard(self):
        cmd = self.create_command(0x00, 0x07, 0x00, 0x5E)
        self.send_command(cmd)

    def set_guard_location_time(self, time_val):
        cmd = self.create_command(0x00, 0x03, 0x00, time_val)
        self.send_command(cmd)
