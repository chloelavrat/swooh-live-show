"""Tests for material/color.py — palette mapping and edge cases."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from material.color import (
    ableton_to_novation,
    rgb_to_novation,
    ABLETON_COLORS,
    NOVATION_COLORS,
    ColorMapper,
)


class TestPaletteData:
    def test_ableton_palette_length(self):
        assert len(ABLETON_COLORS) == 70

    def test_novation_palette_length(self):
        assert len(NOVATION_COLORS) == 128

    def test_ableton_colors_are_rgb_tuples(self):
        for c in ABLETON_COLORS:
            assert len(c) == 3
            assert all(0 <= v <= 255 for v in c)

    def test_novation_colors_are_rgb_tuples(self):
        for c in NOVATION_COLORS:
            assert len(c) == 3
            assert all(0 <= v <= 255 for v in c)


class TestAbletonToNovation:
    def test_returns_int(self):
        result = ableton_to_novation(0)
        assert isinstance(result, int)

    def test_result_in_range(self):
        for i in range(len(ABLETON_COLORS)):
            result = ableton_to_novation(i)
            assert 0 <= result < len(NOVATION_COLORS)

    def test_black_maps_near_off(self):
        # Index 68 in Ableton palette is (0, 0, 0)
        black_idx = next(i for i, c in enumerate(ABLETON_COLORS) if c == (0, 0, 0))
        result = ableton_to_novation(black_idx)
        # Should map to index 0 (Novation off = (0,0,0))
        assert result == 0

    def test_out_of_range_returns_0(self):
        assert ableton_to_novation(-1) == 0
        assert ableton_to_novation(70) == 0
        assert ableton_to_novation(999) == 0

    def test_white_maps_to_high_brightness(self):
        white_idx = next(i for i, c in enumerate(ABLETON_COLORS) if c == (255, 255, 255))
        result = ableton_to_novation(white_idx)
        # Novation index 3 = (255, 255, 255); nearest should be white
        assert result == 3


class TestRgbToNovation:
    def test_pure_black(self):
        assert rgb_to_novation(0, 0, 0) == 0

    def test_pure_white(self):
        result = rgb_to_novation(255, 255, 255)
        assert result == 3   # Novation index 3 = (255, 255, 255)

    def test_pure_red(self):
        result = rgb_to_novation(255, 0, 0)
        r, g, b = NOVATION_COLORS[result]
        # Resulting color should be predominantly red
        assert r > g and r > b

    def test_pure_green(self):
        result = rgb_to_novation(0, 255, 0)
        r, g, b = NOVATION_COLORS[result]
        assert g > r and g > b

    def test_pure_blue(self):
        result = rgb_to_novation(0, 0, 255)
        r, g, b = NOVATION_COLORS[result]
        assert b > r and b > g


class TestColorMapper:
    def test_instance_methods_match_module_functions(self):
        mapper = ColorMapper()
        for i in range(len(ABLETON_COLORS)):
            assert mapper.ableton_to_novation(i) == ableton_to_novation(i)

    def test_rgb_method(self):
        mapper = ColorMapper()
        assert mapper.rgb_to_novation(0, 0, 0) == 0
        assert mapper.rgb_to_novation(255, 255, 255) == 3
