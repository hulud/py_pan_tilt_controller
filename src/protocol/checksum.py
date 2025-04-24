"""
Utilities for calculating and validating checksums for Pelco D protocol.
"""
from typing import List, Union, Iterable


def calculate_checksum(message: Iterable[int]) -> int:
    """
    Calculate the Pelco D checksum for a message.
    
    The checksum is calculated as the sum of all bytes except the sync byte (0xFF),
    modulo 256 (to keep it in the range 0-255).
    
    Args:
        message: Sequence of bytes representing the message (including sync byte)
        
    Returns:
        Calculated checksum as an integer
    """
    # Skip sync byte (first byte) for checksum calculation
    checksum = sum(list(message)[1:]) & 0xFF
    return checksum


def validate_checksum(message: Iterable[int]) -> bool:
    """
    Validate the checksum of a complete Pelco D message.
    
    Args:
        message: Complete message including checksum
        
    Returns:
        True if checksum is valid, False otherwise
    """
    # Extract message without checksum and the provided checksum
    message_bytes = list(message)
    provided_checksum = message_bytes[-1]
    
    # Calculate expected checksum
    expected_checksum = calculate_checksum(message_bytes[:-1])
    
    return provided_checksum == expected_checksum
