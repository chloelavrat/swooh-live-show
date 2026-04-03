"""Tests for protocol/sysex.py — byte correctness and round-trip integrity."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from protocol import sysex
from protocol.constants import NOVATION_SYSEX_HEADER


HEADER = (0xF0,) + NOVATION_SYSEX_HEADER


class TestSetLedRgb:
    def test_correct_framing(self):
        msg = sysex.set_led_rgb(11, 255, 0, 128)
        assert msg[0] == 0xF0
        assert msg[-1] == 0xF7

    def test_contains_header(self):
        msg = sysex.set_led_rgb(11, 255, 0, 128)
        assert msg[:6] == HEADER

    def test_rgb_subcommand(self):
        msg = sysex.set_led_rgb(11, 100, 50, 25)
        # After header (6 bytes): 0x03 (LED), 0x03 (RGB mode), pad, r, g, b
        assert msg[6] == 0x03
        assert msg[7] == 0x03
        assert msg[8] == 11     # pad
        assert msg[9] == 100    # r
        assert msg[10] == 50    # g
        assert msg[11] == 25    # b

    def test_values_masked_to_7bit(self):
        msg = sysex.set_led_rgb(11, 255, 255, 255)
        # 255 & 0x7F = 127
        assert msg[9]  == 127
        assert msg[10] == 127
        assert msg[11] == 127

    def test_total_length(self):
        msg = sysex.set_led_rgb(0, 0, 0, 0)
        # F0(1) + header(5) + 03 03 pad r g b(6) + F7(1) = 13
        assert len(msg) == 13


class TestSetLedPalette:
    def test_framing(self):
        msg = sysex.set_led_palette(36, 5)
        assert msg[0] == 0xF0 and msg[-1] == 0xF7

    def test_palette_subcommand(self):
        msg = sysex.set_led_palette(36, 5)
        assert msg[6] == 0x03
        assert msg[7] == 0x00   # palette mode
        assert msg[8] == 36
        assert msg[9] == 5


class TestSetLedFlash:
    def test_flash_subcommand(self):
        msg = sysex.set_led_flash(20, 3, 7)
        assert msg[7] == 0x01   # flash mode
        assert msg[8] == 20
        assert msg[9] == 3
        assert msg[10] == 7

    def test_length(self):
        msg = sysex.set_led_flash(0, 0, 0)
        # F0(1) + header(5) + 03 01 pad a b(5) + F7(1) = 12
        assert len(msg) == 12


class TestSetLedPulse:
    def test_pulse_subcommand(self):
        msg = sysex.set_led_pulse(15, 9)
        assert msg[7] == 0x02   # pulse mode
        assert msg[8] == 15
        assert msg[9] == 9


class TestBulkLedRgb:
    def test_single_pad(self):
        msg = sysex.bulk_led_rgb([(11, 255, 0, 0)])
        assert msg[0] == 0xF0 and msg[-1] == 0xF7
        assert msg[8] == 11

    def test_multiple_pads(self):
        updates = [(11, 10, 20, 30), (12, 40, 50, 60)]
        msg = sysex.bulk_led_rgb(updates)
        # After F0 + header(5) + 03 03 = index 8 starts pad data
        assert msg[8]  == 11
        assert msg[9]  == 10
        assert msg[10] == 20
        assert msg[11] == 30
        assert msg[12] == 12
        assert msg[13] == 40

    def test_length_scales_with_pads(self):
        updates = [(i, 0, 0, 0) for i in range(8)]
        msg = sysex.bulk_led_rgb(updates)
        # header(8) + 4*8 pads + F7 = 8 + 32 + 1 = 41
        assert len(msg) == 41

    def test_empty_updates(self):
        msg = sysex.bulk_led_rgb([])
        assert msg[0] == 0xF0 and msg[-1] == 0xF7


class TestProgrammerMode:
    def test_on(self):
        msg = sysex.programmer_mode(True)
        # F0 header(5) 0E 01 F7
        assert msg[-1] == 0xF7
        assert msg[-2] == 0x01   # flag
        assert msg[-3] == 0x0E   # command

    def test_off(self):
        msg = sysex.programmer_mode(False)
        assert msg[-1] == 0xF7
        assert msg[-2] == 0x00   # flag off
        assert msg[-3] == 0x0E


class TestDecodePayload:
    def test_strips_framing(self):
        raw = (0xF0, 0x00, 0x20, 0x29, 0xF7)
        result = sysex.decode_payload(raw)
        assert result == (0x00, 0x20, 0x29)

    def test_passthrough_when_no_framing(self):
        raw = (0x00, 0x20, 0x29)
        result = sysex.decode_payload(raw)
        assert result == raw
