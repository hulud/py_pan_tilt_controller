#!/usr/bin/env python3

class OpticalMixin:
    """
    Mixin for optical control functionality
    """
    
    def zoom_in(self):
        cmd = self.create_command(0x00, 0x20, 0x00, 0x00)
        self.send_command(cmd)

    def zoom_out(self):
        cmd = self.create_command(0x00, 0x40, 0x00, 0x00)
        self.send_command(cmd)

    def focus_far(self):
        cmd = self.create_command(0x00, 0x80, 0x00, 0x00)
        self.send_command(cmd)

    def focus_near(self):
        cmd = self.create_command(0x01, 0x00, 0x00, 0x00)
        self.send_command(cmd)

    def iris_open(self):
        cmd = self.create_command(0x02, 0x00, 0x00, 0x00)
        self.send_command(cmd)

    def iris_shut(self):
        cmd = self.create_command(0x04, 0x00, 0x00, 0x00)
        self.send_command(cmd)
