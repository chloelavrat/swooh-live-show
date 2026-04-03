"""
Stubs for _Framework.ControlSurface and _Framework.Task — allow tests outside Ableton.
"""

import sys
from unittest.mock import MagicMock


class MockControlSurface:
    """Minimal ControlSurface stub."""

    def __init__(self, c_instance=None):
        self._c_instance = c_instance
        self._sent = []

    def component_guard(self):
        from contextlib import contextmanager

        @contextmanager
        def _guard():
            yield

        return _guard()

    def _send_midi(self, msg_tuple):
        self._sent.append(msg_tuple)

    def song(self):
        from tests.mocks.live_mock import MockSong
        return MockSong()

    def disconnect(self):
        pass


class MockAdapter:
    """
    Minimal DeviceAdapter stub that records calls for assertions in tests.
    """

    def __init__(self, config_path=None):
        self._calls = []
        self._zones = {}
        self._config_path = config_path
        if config_path:
            self._load_zones()

    def _load_zones(self):
        from material.launchpad_x import LaunchpadXAdapter
        real = LaunchpadXAdapter(lambda x: None, self._config_path)
        self._zones = real._zones

    def zone(self, name: str):
        return self._zones[name]

    def set_pad_rgb(self, pad, r, g, b):
        self._calls.append(("rgb", pad, r, g, b))

    def set_pad_palette(self, pad, color_index):
        self._calls.append(("palette", pad, color_index))

    def set_pad_pulse(self, pad, color_index):
        self._calls.append(("pulse", pad, color_index))

    def set_pad_flash(self, pad, color_a, color_b):
        self._calls.append(("flash", pad, color_a, color_b))

    def clear_pad(self, pad):
        self._calls.append(("clear", pad))

    def clear_all(self):
        self._calls.append(("clear_all",))

    def bulk_set_rgb(self, updates):
        self._calls.append(("bulk_rgb", updates))

    def enter_programmer_mode(self):
        self._calls.append(("prog_on",))

    def exit_programmer_mode(self):
        self._calls.append(("prog_off",))

    def send_note_on(self, note, velocity):
        self._calls.append(("note_on", note, velocity))

    def send_note_off(self, note):
        self._calls.append(("note_off", note))

    def reset_calls(self):
        self._calls.clear()


# Inject _Framework stub into sys.modules so imports don't fail outside Ableton
_framework_stub = MagicMock()
sys.modules.setdefault("_Framework", _framework_stub)
sys.modules.setdefault("_Framework.ControlSurface", _framework_stub)
sys.modules.setdefault("_Framework.Task", _framework_stub)
sys.modules.setdefault("Live", MagicMock())
