"""
DrumPadBehavior — maps a 4×4 pad zone to Drum Rack chains.

Responsibilities:
- Select the corresponding Drum Rack chain in Ableton on pad press.
- Notify the StepSequencer of the new chain/clip target AND active pitch.
- Reflect chain color, mute state, and playhead hit via LEDs.
- Support octave shift (CC 89/79) to move the 16-pad window by 16 notes.
- Color-change mode (hold PAD_COLOR_CHANGE + press drum pad → pick palette color).
"""

from .base import BaseBehavior
from protocol.constants import CC_OCTAVE_UP, CC_OCTAVE_DOWN, PAD_COLOR_CHANGE

# Novation palette indices used by this behavior
COLOR_ARMED_FALLBACK  = 5    # red — chain with no color assigned
COLOR_PLAYING         = 5    # red — note currently playing (flashed on tick)
COLOR_MUTED           = 1    # dark grey (29,29,29)
COLOR_OFF             = 0    # pad off
COLOR_CHANGE_ACTIVE   = 3    # white pulse — color change mode indicator

# 16 palette colors shown in the 4×4 grid during color-change mode.
# Index 0 in this list maps to the top-left pad, index 15 to bottom-right.
DISPLAY_PALETTE = [5, 9, 13, 21, 29, 33, 37, 41, 45, 49, 53, 57, 3, 2, 1, 0]
# 0 = clear override (reset to Ableton color)


class DrumPadBehavior(BaseBehavior):

    ZONE = "drum_pad"
    DEFAULT_ROOT_NOTE = 36   # C1

    def __init__(self, adapter, song, sequencer_ref):
        super().__init__(adapter, song)
        self.root_note  = self.DEFAULT_ROOT_NOTE
        self.sequencer  = sequencer_ref   # StepSequencerBehavior back-reference
        self._zone      = None
        self._selected_pad_index = 0
        # Colour overrides: pad_index → Novation palette index
        self._color_overrides: dict = {}
        # Color-change state: "normal" | "select_pad" | "select_color"
        self._color_state = "normal"
        self._color_change_target_idx = None
        # Playhead tracking: set of pitches currently playing (for flash restore)
        self._prev_playing: set = set()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def on_enter(self):
        try:
            self._zone = self.adapter.zone(self.ZONE)
        except KeyError:
            self._zone = None
            return
        self._refresh_all_leds()

    def on_exit(self):
        if self._zone is None:
            return
        for pad in self._zone.pads:
            self.adapter.clear_pad(pad)
        self.adapter.clear_pad(PAD_COLOR_CHANGE)
        self._color_state = "normal"
        self._prev_playing.clear()

    # ------------------------------------------------------------------
    # Tick — flash pads red when their note is at the playhead
    # ------------------------------------------------------------------

    def tick(self):
        if self._zone is None or self.sequencer is None or self.sequencer.clip is None:
            if self._prev_playing:
                self._restore_pads(self._prev_playing)
                self._prev_playing = set()
            return

        try:
            beat = self.song.current_song_time
            # Grab notes within a 1/16 window at the current position
            raw = self.sequencer.clip.get_notes(beat, 0, 0.25, 128)
            playing = {n[0] for n in raw if not n[4]}   # non-muted pitches
        except Exception:
            playing = set()

        if playing == self._prev_playing:
            return

        newly_on  = playing - self._prev_playing
        newly_off = self._prev_playing - playing

        drum_device = self._get_drum_device()
        chains = list(drum_device.chains) if drum_device else []

        for pitch in newly_on:
            idx = pitch - self.root_note
            if 0 <= idx < len(self._zone.pads):
                self.adapter.set_pad_palette(self._zone.pads[idx], COLOR_PLAYING)

        for pitch in newly_off:
            idx = pitch - self.root_note
            if 0 <= idx < len(self._zone.pads):
                chain = chains[idx] if idx < len(chains) else None
                if chain is None:
                    self.adapter.clear_pad(self._zone.pads[idx])
                else:
                    self._draw_pad(self._zone.pads[idx], idx, chain)

        self._prev_playing = playing

    def _restore_pads(self, pitches: set):
        """Restore pads for a set of pitches to their base color."""
        if self._zone is None:
            return
        drum_device = self._get_drum_device()
        chains = list(drum_device.chains) if drum_device else []
        for pitch in pitches:
            idx = pitch - self.root_note
            if 0 <= idx < len(self._zone.pads):
                chain = chains[idx] if idx < len(chains) else None
                if chain is None:
                    self.adapter.clear_pad(self._zone.pads[idx])
                else:
                    self._draw_pad(self._zone.pads[idx], idx, chain)

    # ------------------------------------------------------------------
    # MIDI handling
    # ------------------------------------------------------------------

    def handle_midi(self, msg) -> bool:
        if self._zone is None:
            return False

        # ── Color-change mode ────────────────────────────────────────────

        if msg.is_note_on and msg.note == PAD_COLOR_CHANGE:
            self._color_state = "select_pad"
            self.adapter.set_pad_pulse(PAD_COLOR_CHANGE, COLOR_CHANGE_ACTIVE)
            return True

        if msg.is_note_off and msg.note == PAD_COLOR_CHANGE:
            was_active = self._color_state != "normal"
            self._color_state = "normal"
            self._color_change_target_idx = None
            if was_active:
                self._refresh_all_leds()
            self.adapter.clear_pad(PAD_COLOR_CHANGE)
            return True

        if self._color_state == "select_pad":
            # Hold color-change + press drum pad → show palette in that zone
            if msg.is_note_on and self._zone.contains(msg.note):
                row, col = self._zone.index_of(msg.note)
                self._color_change_target_idx = row * self._zone.width + col
                self._show_color_palette()
                self._color_state = "select_color"
                return True
            return False   # let other keys through

        if self._color_state == "select_color":
            if msg.is_note_on and self._zone.contains(msg.note):
                row, col = self._zone.index_of(msg.note)
                palette_pos = row * self._zone.width + col
                if 0 <= palette_pos < len(DISPLAY_PALETTE):
                    chosen = DISPLAY_PALETTE[palette_pos]
                    if chosen == 0:
                        self._color_overrides.pop(self._color_change_target_idx, None)
                    else:
                        self._color_overrides[self._color_change_target_idx] = chosen
                self._color_state = "select_pad"   # ready for next pad
                self._color_change_target_idx = None
                self._refresh_all_leds()
                return True
            return False

        # ── Octave shift ─────────────────────────────────────────────────

        if msg.is_cc:
            if msg.cc_number == CC_OCTAVE_UP:
                self.root_note = min(self.root_note + 16, 112)
                self._prev_playing.clear()
                self._refresh_all_leds()
                return True
            if msg.cc_number == CC_OCTAVE_DOWN:
                self.root_note = max(self.root_note - 16, 0)
                self._prev_playing.clear()
                self._refresh_all_leds()
                return True

        # ── Normal drum pad press ─────────────────────────────────────────

        if msg.is_note_on and self._zone.contains(msg.note):
            row, col = self._zone.index_of(msg.note)
            pad_index = row * self._zone.width + col
            self._selected_pad_index = pad_index
            self._select_chain(pad_index)
            return True

        return False

    # ------------------------------------------------------------------
    # Color-change palette
    # ------------------------------------------------------------------

    def _show_color_palette(self):
        if self._zone is None:
            return
        for i, pad in enumerate(self._zone.pads):
            color = DISPLAY_PALETTE[i] if i < len(DISPLAY_PALETTE) else 0
            self.adapter.set_pad_palette(pad, color)

    # ------------------------------------------------------------------
    # Chain selection
    # ------------------------------------------------------------------

    def _chain_for_pad(self, pad_index: int):
        """Return the Live.DrumChain for pad_index, or None."""
        drum_device = self._get_drum_device()
        if drum_device is None:
            return None
        chains = list(drum_device.chains)
        target_note = self.root_note + pad_index
        for chain in chains:
            if hasattr(chain, "note") and chain.note == target_note:
                return chain
        # Fallback: positional
        if pad_index < len(chains):
            return chains[pad_index]
        return None

    def _get_drum_device(self):
        """Return the first drum device on the selected track, or None."""
        try:
            track = self.song.view.selected_track
            for device in track.devices:
                if hasattr(device, "chains"):
                    return device
        except Exception:
            pass
        return None

    def _select_chain(self, pad_index: int):
        chain = self._chain_for_pad(pad_index)
        # Notify sequencer of new pitch and clip
        if self.sequencer is not None:
            pitch = self.root_note + pad_index
            clip  = self._clip_for_chain(chain)
            self.sequencer.set_pitch(pitch)
            self.sequencer.set_clip(clip)
        # Try to select drum pad in Ableton view
        drum_device = self._get_drum_device()
        if drum_device and hasattr(drum_device, "view"):
            try:
                drum_device.view.selected_drum_pad = drum_device.drum_pads[
                    self.root_note + pad_index - drum_device.drum_pads[0].note
                    if hasattr(drum_device, "drum_pads") else pad_index
                ]
            except Exception:
                pass
        self._refresh_all_leds()

    def _clip_for_chain(self, chain):
        """Return the playing/first clip on the selected track, or None."""
        try:
            track = self.song.view.selected_track
            for slot in track.clip_slots:
                if slot.clip is not None:
                    return slot.clip
        except Exception:
            pass
        return None

    # ------------------------------------------------------------------
    # LED helpers
    # ------------------------------------------------------------------

    def _draw_pad(self, pad: int, idx: int, chain):
        """Render a single drum pad based on chain state and color overrides."""
        muted = getattr(chain, "mute", False)
        color = getattr(chain, "color", -1)
        if muted:
            self.adapter.set_pad_palette(pad, COLOR_MUTED)
        elif idx in self._color_overrides:
            self.adapter.set_pad_palette(pad, self._color_overrides[idx])
        elif color >= 0:
            from material.color import ableton_to_novation
            novation_idx = ableton_to_novation(color)
            self.adapter.set_pad_palette(pad, novation_idx if novation_idx else COLOR_ARMED_FALLBACK)
        else:
            self.adapter.set_pad_palette(pad, COLOR_ARMED_FALLBACK)

    def _refresh_all_leds(self):
        if self._zone is None:
            return
        drum_device = self._get_drum_device()
        chains = list(drum_device.chains) if drum_device else []
        for idx, pad in enumerate(self._zone.pads):
            chain = chains[idx] if idx < len(chains) else None
            if chain is None:
                self.adapter.clear_pad(pad)
            else:
                self._draw_pad(pad, idx, chain)

    # ------------------------------------------------------------------
    # State snapshot
    # ------------------------------------------------------------------

    def snapshot(self) -> dict:
        drum_device = self._get_drum_device()
        chains = list(drum_device.chains) if drum_device else []
        pads_state = []
        for idx in range(16):
            chain = chains[idx] if idx < len(chains) else None
            color_rgb = [0, 0, 0]
            muted = False
            playing = (self.root_note + idx) in self._prev_playing
            if chain is not None:
                muted = getattr(chain, "mute", False)
                ableton_color = getattr(chain, "color", -1)
                if ableton_color >= 0:
                    from material.color import ABLETON_COLORS
                    if ableton_color < len(ABLETON_COLORS):
                        color_rgb = list(ABLETON_COLORS[ableton_color])
            pads_state.append({
                "index":     idx,
                "note":      self.root_note + idx,
                "color_rgb": color_rgb,
                "muted":     muted,
                "playing":   playing,
            })
        return {"drum_pads": pads_state}
