#!/usr/bin/env python3

class AuxiliaryMixin:
    """
    Mixin for auxiliary control functionality
    """
    
    def open_aux(self, aux_value=0x00):
        cmd = self.create_command(0x00, 0x09, 0x00, aux_value)
        self.send_command(cmd)

    def shut_aux(self, aux_value=0x00):
        cmd = self.create_command(0x00, 0x0B, 0x00, aux_value)
        self.send_command(cmd)
