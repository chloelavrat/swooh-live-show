"""
LaunchpadXAdapter — DeviceAdapter implementation for Novation Launchpad X.

Loads configs/devices/launchpad_x.json at init, builds Zone objects,
and delegates all LED commands to protocol/sysex.py.
"""

import json
import os

from .base_adapter import DeviceAdapter
from .zone import Zone
from protocol import sysex


class LaunchpadXAdapter(DeviceAdapter):

    def __init__(self, send_midi_fn, config_path: str):
        self._send = send_midi_fn
        self._config = self._load_config(config_path)
        self._zones = self._build_zones()

    # ------------------------------------------------------------------
    # Config + zone setup
    # ------------------------------------------------------------------

    def _load_config(self, path: str) -> dict:
        with open(path, "r") as f:
            return json.load(f)

    def _build_zones(self) -> dict:
        device = self._config["device"]
        grid_cfg = device["grid"]
        pad_offset = grid_cfg["pad_offset"]
        row_stride = grid_cfg["row_stride"]
        zones = {}

        for zone_name, zone_cfg in device.get("zones", {}).items():
            row_min, row_max = zone_cfg["rows"]
            col_min, col_max = zone_cfg["cols"]
            width  = col_max - col_min + 1
            height = row_max - row_min + 1
            pads = []
            for row in range(row_min, row_max + 1):
                for col in range(col_min, col_max + 1):
                    note = pad_offset + col + row * row_stride
                    pads.append(note)
            zones[zone_name] = Zone(
                name=zone_name,
                role=zone_cfg.get("role", ""),
                pads=pads,
                width=width,
                height=height,
            )
        return zones

    def zone(self, name: str) -> Zone:
        return self._zones[name]

    def all_pads(self):
        """Return a flat list of all pad note numbers in the device grid."""
        device = self._config["device"]
        grid = device["grid"]
        pad_offset = grid["pad_offset"]
        row_stride = grid["row_stride"]
        width  = grid["width"]
        height = grid["height"]
        pads = []
        for row in range(height):
            for col in range(width):
                pads.append(pad_offset + col + row * row_stride)
        return pads

    # ------------------------------------------------------------------
    # LED commands
    # ------------------------------------------------------------------

    def set_pad_rgb(self, pad: int, r: int, g: int, b: int):
        self._send(sysex.set_led_rgb(pad, r, g, b))

    def set_pad_palette(self, pad: int, color_index: int):
        self._send(sysex.set_led_palette(pad, color_index))

    def set_pad_pulse(self, pad: int, color_index: int):
        self._send(sysex.set_led_pulse(pad, color_index))

    def set_pad_flash(self, pad: int, color_a: int, color_b: int):
        self._send(sysex.set_led_flash(pad, color_a, color_b))

    def clear_pad(self, pad: int):
        self._send(sysex.set_led_palette(pad, 0))

    def clear_all(self):
        updates = [(p, 0, 0, 0) for p in self.all_pads()]
        if updates:
            self._send(sysex.bulk_led_rgb(updates))

    def bulk_set_rgb(self, updates: list):
        """updates: list of (pad, r, g, b). Single SysEx message."""
        self._send(sysex.bulk_led_rgb(updates))

    # ------------------------------------------------------------------
    # MIDI note output (trigger roll, etc.)
    # ------------------------------------------------------------------

    def send_note_on(self, note: int, velocity: int):
        """Send a Note On via the device MIDI output."""
        self._send((0x90, note & 0x7F, velocity & 0x7F))

    def send_note_off(self, note: int):
        """Send a Note Off via the device MIDI output."""
        self._send((0x80, note & 0x7F, 0))

    # ------------------------------------------------------------------
    # Mode control
    # ------------------------------------------------------------------

    def enter_programmer_mode(self):
        self._send(sysex.programmer_mode(True))

    def exit_programmer_mode(self):
        self._send(sysex.programmer_mode(False))

    # ------------------------------------------------------------------
    # Config accessors
    # ------------------------------------------------------------------

    def cc_map(self) -> dict:
        return self._config["device"].get("cc_map", {})

    def special_pads(self) -> dict:
        return self._config["device"].get("special_pads", {})
