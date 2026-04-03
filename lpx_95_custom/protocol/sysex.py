"""
SysEx encoder for Novation Launchpad X.

All functions return tuple[int, ...] ready for send_midi().
Ableton strips 0xF0/0xF7 from *received* SysEx but expects them when *sending*.

Novation SysEx header: [0x00, 0x20, 0x29, 0x02, 0x0C]
"""

from .constants import NOVATION_SYSEX_HEADER

_START = (0xF0,)
_END   = (0xF7,)
_HDR   = _START + NOVATION_SYSEX_HEADER


def set_led_rgb(pad: int, r: int, g: int, b: int) -> tuple:
    """Single pad RGB: F0 00 20 29 02 0C 03 03 <pad> <r> <g> <b> F7"""
    return _HDR + (0x03, 0x03, pad & 0x7F, r & 0x7F, g & 0x7F, b & 0x7F) + _END


def set_led_palette(pad: int, color_index: int) -> tuple:
    """Single pad palette color: F0 00 20 29 02 0C 03 00 <pad> <color> F7"""
    return _HDR + (0x03, 0x00, pad & 0x7F, color_index & 0x7F) + _END


def set_led_flash(pad: int, color_a: int, color_b: int) -> tuple:
    """Flash between two palette colors: F0 00 20 29 02 0C 03 01 <pad> <a> <b> F7"""
    return _HDR + (0x03, 0x01, pad & 0x7F, color_a & 0x7F, color_b & 0x7F) + _END


def set_led_pulse(pad: int, color_index: int) -> tuple:
    """Pulse (breathe) a palette color: F0 00 20 29 02 0C 03 02 <pad> <color> F7"""
    return _HDR + (0x03, 0x02, pad & 0x7F, color_index & 0x7F) + _END


def bulk_led_rgb(updates: list) -> tuple:
    """
    Batch RGB update — single SysEx message.
    updates: list of (pad, r, g, b) tuples.
    F0 00 20 29 02 0C 03 03 [<pad> <r> <g> <b>]... F7
    """
    payload = ()
    for pad, r, g, b in updates:
        payload += (pad & 0x7F, r & 0x7F, g & 0x7F, b & 0x7F)
    return _HDR + (0x03, 0x03) + payload + _END


def programmer_mode(on: bool) -> tuple:
    """Switch between Live mode (off) and Programmer mode (on)."""
    flag = 0x01 if on else 0x00
    return _HDR + (0x0E, flag) + _END


def decode_payload(raw_bytes) -> tuple:
    """
    Strip framing bytes from a received SysEx payload.
    Ableton delivers without 0xF0/0xF7; this is a no-op but kept for clarity.
    """
    data = tuple(raw_bytes)
    if data and data[0] == 0xF0:
        data = data[1:]
    if data and data[-1] == 0xF7:
        data = data[:-1]
    return data
