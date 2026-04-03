"""Tests for behaviors/step_sequencer.py — note I/O, scroll, playhead."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Inject stubs before importing behaviors
from tests.mocks.framework_mock import MockAdapter
from tests.mocks.live_mock import MockSong, MockClip

import pytest
from behaviors.step_sequencer import StepSequencerBehavior
from protocol.midi import parse


CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), "..", "configs", "devices", "launchpad_x.json"
)


@pytest.fixture
def adapter():
    return MockAdapter(config_path=CONFIG_PATH)


@pytest.fixture
def song():
    return MockSong()


@pytest.fixture
def seq(adapter, song):
    b = StepSequencerBehavior(adapter, song)
    b.on_enter()
    return b


@pytest.fixture
def seq_with_clip(seq):
    clip = MockClip(loop_end=4.0)
    seq.set_clip(clip)
    return seq, clip


class TestLifecycle:
    def test_on_enter_builds_zones(self, seq, adapter):
        assert seq._zone is not None
        assert seq._nav_zone is not None

    def test_on_exit_clears_pads(self, seq, adapter):
        adapter.reset_calls()
        seq.on_exit()
        calls = [c for c in adapter._calls if c[0] in ("clear", "bulk_rgb")]
        assert len(calls) > 0


class TestSetClip:
    def test_set_clip_assigns(self, seq):
        clip = MockClip()
        seq.set_clip(clip)
        assert seq.clip is clip

    def test_set_clip_replaces(self, seq):
        clip1 = MockClip()
        clip2 = MockClip()
        seq.set_clip(clip1)
        seq.set_clip(clip2)
        assert seq.clip is clip2

    def test_set_none_clears(self, seq):
        seq.set_clip(MockClip())
        seq.set_clip(None)
        assert seq.clip is None


class TestNoteInsertDelete:
    def test_insert_note_on_empty_step(self, seq_with_clip, adapter):
        seq, clip = seq_with_clip
        # Press step (0,0) → beat_time 0.0 — inserts at active pitch (36)
        pad = seq._zone.pad_at(0, 0)
        seq.handle_midi(parse(0x90, pad, 100))
        notes = clip.get_notes(0.0, 36, 0.25, 1)
        assert len(notes) == 1

    def test_delete_note_on_filled_step(self, seq_with_clip, adapter):
        seq, clip = seq_with_clip
        # Manually insert a note at active pitch
        clip.set_notes(((36, 0.0, 0.225, 100, False),))
        # Press same step → should delete
        pad = seq._zone.pad_at(0, 0)
        seq.handle_midi(parse(0x90, pad, 100))
        notes = clip.get_notes(0.0, 36, 0.25, 1)
        assert len(notes) == 0

    def test_insert_on_second_step(self, seq_with_clip):
        seq, clip = seq_with_clip
        pad = seq._zone.pad_at(0, 1)
        seq.handle_midi(parse(0x90, pad, 100))
        notes = clip.get_notes(0.25, 36, 0.25, 1)
        assert len(notes) == 1

    def test_set_pitch_changes_active_pitch(self, seq_with_clip):
        seq, clip = seq_with_clip
        seq.set_pitch(38)
        assert seq._active_pitch == 38
        # Insert note — should use pitch 38
        pad = seq._zone.pad_at(0, 0)
        seq.handle_midi(parse(0x90, pad, 100))
        notes = clip.get_notes(0.0, 38, 0.25, 1)
        assert len(notes) == 1

    def test_set_pitch_hides_other_pitches(self, seq_with_clip):
        seq, clip = seq_with_clip
        # Insert kick (36) then switch to snare (38) — kick should not appear
        clip.set_notes(((36, 0.0, 0.225, 100, False),))
        seq.set_pitch(38)
        notes_in_view = seq._notes_in_view()
        assert all(n is None for n in notes_in_view)


class TestScrollOffset:
    def test_nav_press_scrolls(self, seq_with_clip, adapter):
        seq, clip = seq_with_clip
        nav_pad = seq._nav_zone.pads[2]   # beat 2
        seq.handle_midi(parse(0x90, nav_pad, 100))
        # scroll_offset should be beat 2 / 0.25 = 8 steps
        assert seq.scroll_offset == 8

    def test_scroll_zero_by_default(self, seq_with_clip):
        seq, _ = seq_with_clip
        assert seq.scroll_offset == 0


class TestPlayhead:
    def test_playhead_advances(self, seq_with_clip, song):
        seq, _ = seq_with_clip
        song.advance_time(0.25)
        assert seq._playhead_step == 1

    def test_playhead_wraps(self, seq_with_clip, song):
        seq, _ = seq_with_clip
        # 64 steps × 0.25 beats = 16 beats
        song.advance_time(16.0)
        assert seq._playhead_step == 0


class TestSnapshot:
    def test_snapshot_returns_step_grid(self, seq_with_clip):
        seq, clip = seq_with_clip
        clip.set_notes(((36, 0.0, 0.225, 100, False),))
        snap = seq.snapshot()
        assert "step_grid" in snap
        assert snap["step_grid"]["clip_length_beats"] == 4.0

    def test_snapshot_active_step(self, seq_with_clip):
        seq, clip = seq_with_clip
        clip.set_notes(((36, 0.0, 0.225, 80, False),))
        snap = seq.snapshot()
        step0 = snap["step_grid"]["steps"][0]
        assert step0["active"] is True
        assert step0["velocity"] == 80
