#!/usr/bin/env python3

class MovementMixin:
    """
    Mixin for basic movement commands
    """
    
    def move_up(self, speed=0x20):
        cmd = self.create_command(0x00, 0x08, 0x00, speed)
        self.send_command(cmd)

    def move_down(self, speed=0x20):
        cmd = self.create_command(0x00, 0x10, 0x00, speed)
        self.send_command(cmd)

    def move_left(self, speed=0x20):
        cmd = self.create_command(0x00, 0x04, speed, 0x00)
        self.send_command(cmd)

    def move_right(self, speed=0x20):
        cmd = self.create_command(0x00, 0x02, speed, 0x00)
        self.send_command(cmd)

    def stop(self):
        cmd = self.create_command(0x00, 0x00, 0x00, 0x00)
        self.send_command(cmd)

    def move_left_up(self, pan_speed=0x20, tilt_speed=0x20):
        cmd = self.create_command(0x00, 0x0C, pan_speed, tilt_speed)
        self.send_command(cmd)

    def move_left_down(self, pan_speed=0x20, tilt_speed=0x20):
        cmd = self.create_command(0x00, 0x14, pan_speed, tilt_speed)
        self.send_command(cmd)

    def move_right_up(self, pan_speed=0x20, tilt_speed=0x20):
        cmd = self.create_command(0x00, 0x0A, pan_speed, tilt_speed)
        self.send_command(cmd)

    def move_right_down(self, pan_speed=0x20, tilt_speed=0x20):
        cmd = self.create_command(0x00, 0x12, pan_speed, tilt_speed)
        self.send_command(cmd)
