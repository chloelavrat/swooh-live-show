"""
StepSequencerBehavior — 8×8 step grid view of the selected Drum Rack clip.

Grid layout:
  - rows 0–7 (bottom to top) = visual rows (irreversed in display; top=row7 = "most visible")
  - cols 0–7 = 8 steps per row
  - Total: 64 steps of 1/16 each = 4 bars by default

Row 8 (clip_length zone): beat-position / scroll navigation (read-only press → scroll).
When playhead is outside the visible window the nav row pad for the current beat flashes red.
"""

from .base import BaseBehavior

# Novation palette indices
COLOR_EMPTY          = 0    # off
COLOR_STEP_DIM       = 21   # dim green — low velocity
COLOR_STEP_BRIGHT    = 23   # bright green — high velocity
COLOR_PLAYHEAD       = 9    # amber / orange
COLOR_MUTED          = 1    # dark grey
COLOR_MUTED_PLAYING  = 5    # red — muted note at playhead position
COLOR_OUT_OF_VIEW    = 5    # red flash on nav row — notes outside visible window
COLOR_CLIP_IN_VIEW   = 3    # bright white
COLOR_CLIP_CONTENT   = 2    # dim grey


class StepSequencerBehavior(BaseBehavior):

    ZONE          = "step_sequencer"
    CLIP_NAV_ZONE = "clip_length"
    STEP_LENGTH   = 0.25   # 1/16 in beats
    # GRID_COLS / GRID_ROWS are derived from the zone at on_enter().
    GRID_COLS     = 8
    GRID_ROWS     = 8

    def __init__(self, adapter, song):
        super().__init__(adapter, song)
        self.clip           = None
        self.scroll_offset  = 0    # in steps
        self._active_pitch  = 36   # pitch edited by the step grid (set by DrumPadBehavior)
        self._playhead_step = -1
        self._out_of_view   = False  # True when playhead is outside visible window
        self._zone          = None
        self._nav_zone      = None
        self._song_listener = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def on_enter(self):
        try:
            self._zone     = self.adapter.zone(self.ZONE)
            self._nav_zone = self.adapter.zone(self.CLIP_NAV_ZONE)
        except KeyError:
            return
        # Use actual zone dimensions (hardware may differ from class defaults)
        self.GRID_COLS = self._zone.width
        self.GRID_ROWS = self._zone.height
        self._attach_song_listener()
        self._draw_grid()
        self._draw_nav_row()

    def on_exit(self):
        self._detach_song_listener()
        if self._zone:
            for pad in self._zone.pads:
                self.adapter.clear_pad(pad)
        if self._nav_zone:
            for pad in self._nav_zone.pads:
                self.adapter.clear_pad(pad)

    # ------------------------------------------------------------------
    # Active pitch (set by DrumPadBehavior on chain selection)
    # ------------------------------------------------------------------

    def set_pitch(self, pitch: int):
        """Switch the pitch being edited and redraw the grid."""
        if pitch == self._active_pitch:
            return
        self._active_pitch = pitch
        self._draw_grid()
        self._draw_nav_row()

    # ------------------------------------------------------------------
    # Song time listener (playhead)
    # ------------------------------------------------------------------

    def _attach_song_listener(self):
        if not self._song_listener:
            try:
                self.song.add_current_song_time_listener(self._on_song_time_changed)
                self._song_listener = True
            except Exception:
                pass

    def _detach_song_listener(self):
        if self._song_listener:
            try:
                self.song.remove_current_song_time_listener(self._on_song_time_changed)
            except Exception:
                pass
            self._song_listener = False

    def _on_song_time_changed(self):
        if self.clip is None or self._zone is None:
            return
        try:
            beat = self.song.current_song_time
        except Exception:
            return

        # Compute step relative to the clip loop (not grid-modulo)
        try:
            clip_len = max(float(self.clip.loop_end), self.STEP_LENGTH)
            beat_in_loop = beat % clip_len
        except Exception:
            clip_len = self.STEP_LENGTH
            beat_in_loop = 0.0
        abs_step = int(beat_in_loop / self.STEP_LENGTH)

        # Determine whether playhead falls within the visible window
        view_start = self.scroll_offset
        view_end   = self.scroll_offset + self.GRID_COLS * self.GRID_ROWS
        in_view    = view_start <= abs_step < view_end

        if in_view:
            was_out = self._out_of_view
            self._out_of_view = False
            grid_step = abs_step - self.scroll_offset
            if was_out:
                # Restore nav row that may have had a red flash
                self._draw_nav_row()
            if grid_step != self._playhead_step:
                old = self._playhead_step
                self._playhead_step = grid_step
                self._update_playhead(old, grid_step)
        else:
            self._out_of_view = True
            # Flash the nav row pad for the current beat red to signal out-of-view action
            if self._nav_zone is not None:
                try:
                    beat_idx = int(beat_in_loop)
                    if 0 <= beat_idx < len(self._nav_zone.pads):
                        self.adapter.set_pad_flash(
                            self._nav_zone.pads[beat_idx], COLOR_OUT_OF_VIEW, 0
                        )
                except Exception:
                    pass

    def _update_playhead(self, old_step: int, new_step: int):
        """Redraw only the two affected columns to minimise SysEx traffic."""
        self._draw_col(old_step % self.GRID_COLS)
        self._draw_col(new_step % self.GRID_COLS)

    # ------------------------------------------------------------------
    # Clip management
    # ------------------------------------------------------------------

    def set_clip(self, clip):
        """Switch the watched clip and redraw."""
        if self.clip is not None:
            try:
                self.clip.remove_notes_listener(self._draw_grid)
            except Exception:
                pass
        self.clip = clip
        if clip is not None:
            try:
                clip.add_notes_listener(self._draw_grid)
            except Exception:
                pass
        self._draw_grid()
        self._draw_nav_row()

    # ------------------------------------------------------------------
    # Note helpers
    # ------------------------------------------------------------------

    def _notes_in_view(self) -> list:
        """
        Return list of (GRID_ROWS * GRID_COLS) entries: None or note tuple.
        Filtered to self._active_pitch only.
        """
        result = [None] * (self.GRID_COLS * self.GRID_ROWS)
        if self.clip is None:
            return result
        try:
            start_beat = self.scroll_offset * self.STEP_LENGTH
            notes = self.clip.get_notes(
                start_beat,
                self._active_pitch,
                self.GRID_COLS * self.GRID_ROWS * self.STEP_LENGTH,
                1,   # pitch span = 1 → exact pitch only
            )
            for note in notes:
                pitch, time, duration, velocity, muted = note
                step_idx = int((time - start_beat) / self.STEP_LENGTH)
                if 0 <= step_idx < len(result):
                    result[step_idx] = note
        except Exception:
            pass
        return result

    def _velocity_to_color(self, velocity: int) -> int:
        """Map velocity 1–127 → Novation palette index (dim→bright green)."""
        ratio = max(0, min(127, velocity)) / 127.0
        return COLOR_STEP_DIM + int(ratio * (COLOR_STEP_BRIGHT - COLOR_STEP_DIM))

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------

    def _draw_grid(self):
        if self._zone is None:
            return
        notes = self._notes_in_view()
        playhead_col = self._playhead_step % self.GRID_COLS if self._playhead_step >= 0 else -1

        updates = []
        for row in range(self.GRID_ROWS):
            for col in range(self.GRID_COLS):
                step_idx = row * self.GRID_COLS + col
                pad = self._zone.pad_at(row, col)
                note = notes[step_idx]

                if note is not None:
                    _, _, _, velocity, muted = note
                    if muted:
                        color = COLOR_MUTED
                    else:
                        color = self._velocity_to_color(velocity)
                else:
                    color = COLOR_EMPTY

                updates.append((pad, *self._palette_to_rgb(color)))

        self.adapter.bulk_set_rgb(updates)

        # Overlay playhead column
        if 0 <= playhead_col < self.GRID_COLS:
            self._draw_playhead_col(playhead_col)

    def _draw_col(self, col: int):
        """Redraw a single column (used for playhead updates)."""
        if self._zone is None or col < 0 or col >= self.GRID_COLS:
            return
        notes = self._notes_in_view()
        playhead_col = self._playhead_step % self.GRID_COLS if self._playhead_step >= 0 else -1
        is_playhead = (col == playhead_col)

        for row in range(self.GRID_ROWS):
            step_idx = row * self.GRID_COLS + col
            pad = self._zone.pad_at(row, col)
            note = notes[step_idx]

            if is_playhead:
                if note is not None and note[4]:
                    # Muted note at playhead → red pulse to signal it's playing but muted
                    self.adapter.set_pad_pulse(pad, COLOR_MUTED_PLAYING)
                else:
                    # Normal amber playhead (may have a note underneath — still amber)
                    self.adapter.set_pad_rgb(pad, 255, 128, 0)
            elif note is not None:
                _, _, _, velocity, muted = note
                color = COLOR_MUTED if muted else self._velocity_to_color(velocity)
                r, g, b = self._palette_to_rgb(color)
                self.adapter.set_pad_rgb(pad, r, g, b)
            else:
                self.adapter.clear_pad(pad)

    def _draw_playhead_col(self, col: int):
        if self._zone is None:
            return
        for row in range(self.GRID_ROWS):
            pad = self._zone.pad_at(row, col)
            self.adapter.set_pad_rgb(pad, 255, 128, 0)

    def _draw_nav_row(self):
        if self._nav_zone is None or self.clip is None:
            return
        try:
            clip_length_beats = self.clip.loop_end
        except Exception:
            clip_length_beats = 0.0

        view_start_beat = self.scroll_offset * self.STEP_LENGTH
        view_end_beat   = view_start_beat + self.GRID_COLS * self.STEP_LENGTH

        for i, pad in enumerate(self._nav_zone.pads):
            beat = float(i)
            if beat < clip_length_beats:
                if view_start_beat <= beat < view_end_beat:
                    self.adapter.set_pad_palette(pad, COLOR_CLIP_IN_VIEW)
                else:
                    self.adapter.set_pad_palette(pad, COLOR_CLIP_CONTENT)
            else:
                self.adapter.clear_pad(pad)

    # ------------------------------------------------------------------
    # MIDI handling
    # ------------------------------------------------------------------

    def handle_midi(self, msg) -> bool:
        if self._zone is None:
            return False

        # Step grid press
        if msg.is_note_on and self._zone.contains(msg.note):
            row, col = self._zone.index_of(msg.note)
            self._toggle_step(row, col)
            return True

        # Nav row press → scroll
        if self._nav_zone and msg.is_note_on and self._nav_zone.contains(msg.note):
            idx = self._nav_zone.pads.index(msg.note)
            beat = float(idx)
            self.scroll_offset = int(beat / self.STEP_LENGTH)
            self._out_of_view = False
            self._draw_grid()
            self._draw_nav_row()
            return True

        return False

    def _toggle_step(self, row: int, col: int):
        """Insert note at active pitch if empty, delete if filled."""
        if self.clip is None:
            return
        step_idx  = row * self.GRID_COLS + col
        beat_time = (self.scroll_offset + step_idx) * self.STEP_LENGTH
        try:
            notes = self.clip.get_notes(beat_time, self._active_pitch, self.STEP_LENGTH, 1)
            if notes:
                self.clip.remove_notes(beat_time, self._active_pitch, self.STEP_LENGTH, 1)
            else:
                note = (self._active_pitch, beat_time, self.STEP_LENGTH * 0.9, 100, False)
                self.clip.set_notes((note,))
        except Exception:
            pass
        self._draw_col(col)

    # ------------------------------------------------------------------
    # Palette helper (simplified RGB mapping from palette index)
    # ------------------------------------------------------------------

    def _palette_to_rgb(self, index: int):
        from material.color import NOVATION_COLORS
        if 0 <= index < len(NOVATION_COLORS):
            return NOVATION_COLORS[index]
        return (0, 0, 0)

    # ------------------------------------------------------------------
    # State snapshot
    # ------------------------------------------------------------------

    def snapshot(self) -> dict:
        clip_length = 0.0
        if self.clip is not None:
            try:
                clip_length = float(self.clip.loop_end)
            except Exception:
                pass

        notes = self._notes_in_view()
        steps_state = []
        for idx, note in enumerate(notes):
            row = idx // self.GRID_COLS
            col = idx % self.GRID_COLS
            if note is not None:
                _, _, _, velocity, muted = note
                steps_state.append({
                    "col":      col,
                    "row":      row,
                    "active":   True,
                    "velocity": int(velocity),
                    "muted":    bool(muted),
                })
            else:
                steps_state.append({
                    "col":      col,
                    "row":      row,
                    "active":   False,
                    "velocity": 0,
                    "muted":    False,
                })

        return {
            "step_grid": {
                "clip_length_beats":   clip_length,
                "scroll_offset_steps": self.scroll_offset,
                "active_pitch":        self._active_pitch,
                "steps":               steps_state,
            }
        }
