#!/usr/bin/env python3

class PresetsMixin:
    """
    Mixin for preset management functionality
    """
    
    def set_preset(self, preset):
        cmd = self.create_command(0x00, 0x03, 0x00, preset)
        self.send_command(cmd)

    def call_preset(self, preset):
        cmd = self.create_command(0x00, 0x07, 0x00, preset)
        self.send_command(cmd)

    def delete_preset(self, preset):
        cmd = self.create_command(0x00, 0x05, 0x00, preset)
        self.send_command(cmd)
