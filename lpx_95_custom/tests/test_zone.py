"""Tests for material/zone.py — geometry helpers."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from material.zone import Zone


@pytest.fixture
def drum_zone():
    """4×4 drum pad zone, pads 11–44 (simplified linear for testing)."""
    pads = list(range(11, 11 + 16))   # 16 pads
    return Zone(name="drum_pad", role="drum_selector", pads=pads, width=4, height=4)


@pytest.fixture
def seq_zone():
    """8×8 step sequencer zone."""
    pads = list(range(50, 50 + 64))
    return Zone(name="step_sequencer", role="step_grid", pads=pads, width=8, height=8)


class TestPadAt:
    def test_origin(self, drum_zone):
        assert drum_zone.pad_at(0, 0) == 11

    def test_first_row_last_col(self, drum_zone):
        assert drum_zone.pad_at(0, 3) == 14

    def test_second_row_first_col(self, drum_zone):
        assert drum_zone.pad_at(1, 0) == 15

    def test_top_right(self, drum_zone):
        assert drum_zone.pad_at(3, 3) == 26

    def test_out_of_bounds_row(self, drum_zone):
        with pytest.raises(IndexError):
            drum_zone.pad_at(4, 0)

    def test_out_of_bounds_col(self, drum_zone):
        with pytest.raises(IndexError):
            drum_zone.pad_at(0, 4)

    def test_negative_row(self, drum_zone):
        with pytest.raises(IndexError):
            drum_zone.pad_at(-1, 0)


class TestIndexOf:
    def test_first_pad(self, drum_zone):
        assert drum_zone.index_of(11) == (0, 0)

    def test_second_pad_same_row(self, drum_zone):
        assert drum_zone.index_of(12) == (0, 1)

    def test_second_row(self, drum_zone):
        assert drum_zone.index_of(15) == (1, 0)

    def test_last_pad(self, drum_zone):
        assert drum_zone.index_of(26) == (3, 3)

    def test_unknown_pad(self, drum_zone):
        with pytest.raises(ValueError):
            drum_zone.index_of(99)

    def test_roundtrip(self, seq_zone):
        """pad_at(index_of(pad)) == pad for all pads."""
        for pad in seq_zone.pads:
            row, col = seq_zone.index_of(pad)
            assert seq_zone.pad_at(row, col) == pad


class TestContains:
    def test_known_pad(self, drum_zone):
        assert drum_zone.contains(11) is True

    def test_unknown_pad(self, drum_zone):
        assert drum_zone.contains(99) is False

    def test_boundary(self, drum_zone):
        assert drum_zone.contains(26) is True   # last pad

    def test_just_outside(self, drum_zone):
        assert drum_zone.contains(27) is False


class TestLaunchpadXZones:
    """Integration: verify zones built from the real JSON config."""

    @pytest.fixture
    def adapter(self):
        from tests.mocks.framework_mock import MockAdapter
        config = os.path.join(
            os.path.dirname(__file__), "..", "configs", "devices", "launchpad_x.json"
        )
        return MockAdapter(config_path=config)

    def test_drum_pad_zone_size(self, adapter):
        z = adapter.zone("drum_pad")
        assert z.width == 4 and z.height == 4
        assert len(z.pads) == 16

    def test_step_sequencer_zone_size(self, adapter):
        z = adapter.zone("step_sequencer")
        assert z.width == 8 and z.height == 4
        assert len(z.pads) == 32

    def test_clip_length_zone(self, adapter):
        z = adapter.zone("clip_length")
        assert z.width == 8 and z.height == 1

    def test_bottom_left_pad(self, adapter):
        z = adapter.zone("drum_pad")
        # pad_offset=11, row_stride=10, rows=[0,3], cols=[0,3]
        assert z.pad_at(0, 0) == 11
