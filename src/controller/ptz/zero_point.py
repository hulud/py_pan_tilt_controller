"""
Zero-point initialisation moved out of the main class
to keep core.py concise.
"""

import logging
import time


log = logging.getLogger(__name__)


def run(controller, retries: int = 3) -> None:
    """
    Fire-and-forget zeroing on pan & tilt – we don't read any ACK.
    """
    log.info("Zeroing pan and tilt (fire-and-forget)…")
    controller._send_command(controller.protocol.set_pan_zero_point())
    # Add delay between commands to give device time to process
    time.sleep(0.2)
    controller._send_command(controller.protocol.set_tilt_zero_point())
    # Allow device to settle after zero-point commands
    time.sleep(0.3)
    
    # Flush any response bytes that might have been sent
    try:
        controller.connection.receive(size=64, timeout=0.1)
    except Exception:
        pass
