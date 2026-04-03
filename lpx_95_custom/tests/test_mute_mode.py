"""Tests for behaviors/mute_mode.py — momentary/latch FSM transitions."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tests.mocks.framework_mock import MockAdapter
from tests.mocks.live_mock import MockSong, MockDrumChain, MockDevice, MockTrack, MockView

import pytest
from behaviors.mute_mode import MuteModeBehavior
from protocol.midi import parse
from protocol.constants import PAD_MUTE_BUTTON, PAD_MUTE_MODE_CHANGE


CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), "..", "configs", "devices", "launchpad_x.json"
)


@pytest.fixture
def adapter():
    return MockAdapter(config_path=CONFIG_PATH)


@pytest.fixture
def song_with_chains():
    song = MockSong()
    chains = [MockDrumChain(f"Chain{i}", 36 + i, 5, False) for i in range(4)]
    device = MockDevice(chains=chains)
    track = MockTrack(device=device)
    song.view = MockView(track=track)
    return song


@pytest.fixture
def mute(adapter, song_with_chains):
    b = MuteModeBehavior(adapter, song_with_chains)
    b.on_enter()
    return b, adapter, song_with_chains


class TestMomentaryMode:
    def test_default_mode_is_momentary(self, mute):
        b, _, _ = mute
        assert b.mode == MuteModeBehavior.MODE_MOMENTARY

    def test_mute_pad_hold_sets_flag(self, mute):
        b, _, _ = mute
        b.handle_midi(parse(0x90, PAD_MUTE_BUTTON, 127))
        assert b._mute_held is True

    def test_mute_pad_release_clears_flag(self, mute):
        b, _, _ = mute
        b.handle_midi(parse(0x90, PAD_MUTE_BUTTON, 127))
        b.handle_midi(parse(0x80, PAD_MUTE_BUTTON, 0))
        assert b._mute_held is False

    def test_drum_pad_press_while_held_toggles_mute(self, mute):
        b, adapter, song = mute
        drum_zone = adapter.zone("drum_pad")
        pad0 = drum_zone.pads[0]

        # Hold Mute
        b.handle_midi(parse(0x90, PAD_MUTE_BUTTON, 127))
        # Press first drum pad
        b.handle_midi(parse(0x90, pad0, 100))

        # The first chain should now be muted
        chain = song.view.selected_track.devices[0].chains[0]
        assert chain.mute is True

    def test_toggle_back_unmutes(self, mute):
        b, adapter, song = mute
        drum_zone = adapter.zone("drum_pad")
        pad0 = drum_zone.pads[0]
        chain = song.view.selected_track.devices[0].chains[0]
        chain.mute = True

        b.handle_midi(parse(0x90, PAD_MUTE_BUTTON, 127))
        b.handle_midi(parse(0x90, pad0, 100))

        assert chain.mute is False


class TestLatchMode:
    def test_mute_mode_change_pad_enters_latch(self, mute):
        b, _, _ = mute
        b.handle_midi(parse(0x90, PAD_MUTE_MODE_CHANGE, 100))
        assert b.mode == MuteModeBehavior.MODE_LATCH

    def test_mute_mode_change_pad_exits_latch(self, mute):
        b, _, _ = mute
        b.handle_midi(parse(0x90, PAD_MUTE_MODE_CHANGE, 100))
        b.handle_midi(parse(0x90, PAD_MUTE_MODE_CHANGE, 100))
        assert b.mode == MuteModeBehavior.MODE_MOMENTARY

    def test_toggle_mode_enters_latch(self, mute):
        b, _, _ = mute
        b.toggle_mode()
        assert b.mode == MuteModeBehavior.MODE_LATCH

    def test_toggle_mode_back_to_momentary(self, mute):
        b, _, _ = mute
        b.toggle_mode()
        b.toggle_mode()
        assert b.mode == MuteModeBehavior.MODE_MOMENTARY

    def test_latch_stages_pad_press_while_mute_held(self, mute):
        """Option B: hold Mute + press drum pad → staged (green pulse)."""
        b, adapter, _ = mute
        b.toggle_mode()
        drum_zone = adapter.zone("drum_pad")
        pad0 = drum_zone.pads[0]

        b.handle_midi(parse(0x90, PAD_MUTE_BUTTON, 127))   # hold Mute
        b.handle_midi(parse(0x90, pad0, 100))               # stage pad0
        assert 0 in b._pending_mutes
        # Staged pad should be lit green (pulse color index 21)
        pulse_calls = [c for c in adapter._calls if c[0] == "pulse" and c[1] == pad0]
        assert any(c[2] == 21 for c in pulse_calls)

    def test_latch_direct_toggle_without_mute(self, mute):
        """Option A: tap drum pad without Mute held → immediate toggle."""
        b, _, song = mute
        b.toggle_mode()
        chain = song.view.selected_track.devices[0].chains[0]

        # No Mute held — direct tap should toggle immediately
        from tests.mocks.framework_mock import MockAdapter as _MA
        drum_zone = b._drum_zone
        pad0 = drum_zone.pads[0]
        b.handle_midi(parse(0x90, pad0, 100))
        assert chain.mute is True
        # Mode stays latch
        assert b.mode == MuteModeBehavior.MODE_LATCH

    def test_latch_unstages_second_press_while_mute_held(self, mute):
        b, adapter, _ = mute
        b.toggle_mode()
        drum_zone = adapter.zone("drum_pad")
        pad0 = drum_zone.pads[0]

        b.handle_midi(parse(0x90, PAD_MUTE_BUTTON, 127))   # hold Mute
        b.handle_midi(parse(0x90, pad0, 100))               # stage
        b.handle_midi(parse(0x90, pad0, 100))               # un-stage
        assert 0 not in b._pending_mutes

    def test_mute_pad_release_commits_pending(self, mute):
        """Option B commit: staged pads applied on Mute pad release (not press)."""
        b, adapter, song = mute
        b.toggle_mode()
        drum_zone = adapter.zone("drum_pad")
        pad0 = drum_zone.pads[0]
        chain = song.view.selected_track.devices[0].chains[0]

        b.handle_midi(parse(0x90, PAD_MUTE_BUTTON, 127))   # hold Mute
        b.handle_midi(parse(0x90, pad0, 100))               # stage
        assert chain.mute is False                          # not yet applied
        b.handle_midi(parse(0x80, PAD_MUTE_BUTTON, 0))     # release → commit

        assert chain.mute is True
        # Mode stays latch (does NOT exit to momentary)
        assert b.mode == MuteModeBehavior.MODE_LATCH

    def test_commit_clears_pending(self, mute):
        b, adapter, _ = mute
        b.toggle_mode()
        drum_zone = adapter.zone("drum_pad")
        pad0 = drum_zone.pads[0]

        b.handle_midi(parse(0x90, PAD_MUTE_BUTTON, 127))   # hold
        b.handle_midi(parse(0x90, pad0, 100))               # stage
        b.handle_midi(parse(0x80, PAD_MUTE_BUTTON, 0))     # release → commit

        assert len(b._pending_mutes) == 0

    def test_armed_pads_pulse_in_latch(self, mute):
        """Armed (non-muted) pads should pulse in latch mode (fondu clignotant)."""
        b, adapter, _ = mute
        adapter.reset_calls()
        b.toggle_mode()   # enter latch → triggers _refresh_pad_states
        pulse_calls = [c for c in adapter._calls if c[0] == "pulse"]
        # At least the Mute pad (amber) + some drum pads (green) should pulse
        assert len(pulse_calls) >= 2


class TestSnapshot:
    def test_snapshot_contains_mode(self, mute):
        b, _, _ = mute
        snap = b.snapshot()
        assert snap["mute_mode"] == "momentary"

    def test_snapshot_reflects_toggle(self, mute):
        b, _, _ = mute
        b.toggle_mode()
        snap = b.snapshot()
        assert snap["mute_mode"] == "latch"
