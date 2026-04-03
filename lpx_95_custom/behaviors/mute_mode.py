"""
MuteModeBehavior — momentary and latch mute control.

Sub-modes:
  MOMENTARY (default): Hold Mute pad + press drum pad → mute/unmute immediately on release.

  LATCH (enter/exit via PAD_MUTE_MODE_CHANGE):
    Option A — direct: tap a drum pad (no Mute held) → immediate toggle.
    Option B — staged: hold Mute pad + tap drum pads → they pulse green (staged);
               release Mute → all staged pads are committed.
    Mute pad stays amber-pulse in latch. All armed pads pulse (fondu clignotant).
    Exit latch by pressing PAD_MUTE_MODE_CHANGE again.
"""

from .base import BaseBehavior
from protocol.constants import PAD_MUTE_BUTTON, PAD_MUTE_MODE_CHANGE

# Novation palette indices
COLOR_MUTED        = 1    # dark grey
COLOR_ARMED_PULSE  = 21   # green pulse — armed pad in latch mode (fondu clignotant)
COLOR_STAGED       = 21   # green pulse — same hue as armed, brighter visually via pulse
COLOR_LATCH_ACTIVE = 9    # amber pulse — Mute pad when in latch mode
COLOR_OFF          = 0


class MuteModeBehavior(BaseBehavior):

    MODE_MOMENTARY = "momentary"
    MODE_LATCH     = "latch"

    def __init__(self, adapter, song):
        super().__init__(adapter, song)
        self.mode            = self.MODE_MOMENTARY
        self._mute_held      = False    # True while Mute pad is physically held
        self._pending_mutes  = set()    # pad indices staged during Mute-hold in latch
        self._drum_zone      = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def on_enter(self):
        try:
            self._drum_zone = self.adapter.zone("drum_pad")
        except KeyError:
            self._drum_zone = None

    def on_exit(self):
        pass

    # ------------------------------------------------------------------
    # MIDI handling
    # ------------------------------------------------------------------

    def handle_midi(self, msg) -> bool:
        # --- Mute Mode Change pad — enter/exit latch ---
        if msg.is_note_on and msg.note == PAD_MUTE_MODE_CHANGE:
            self.toggle_mode()
            return True

        # --- Mute pad press (both modes: start holding) ---
        if msg.is_note_on and msg.note == PAD_MUTE_BUTTON:
            self._mute_held = True
            return True

        # --- Mute pad release ---
        if msg.is_note_off and msg.note == PAD_MUTE_BUTTON:
            if self._mute_held:
                self._mute_held = False
                if self.mode == self.MODE_LATCH and self._pending_mutes:
                    # Option B commit: apply all staged on release
                    self._apply_mutes()
                    self._pending_mutes.clear()
                    self._refresh_pad_states()
            return True

        # --- Drum pad press while Mute held ---
        if self._mute_held and self._drum_zone and msg.is_note_on:
            if self._drum_zone.contains(msg.note):
                row, col = self._drum_zone.index_of(msg.note)
                pad_index = row * self._drum_zone.width + col
                if self.mode == self.MODE_MOMENTARY:
                    # Momentary: immediate toggle
                    self._toggle_mute(pad_index)
                else:
                    # Latch Option B: stage / unstage
                    if pad_index in self._pending_mutes:
                        self._pending_mutes.discard(pad_index)
                    else:
                        self._pending_mutes.add(pad_index)
                    self._refresh_pad_states()
                return True

        # --- Drum pad press in latch WITHOUT Mute held → Option A: immediate toggle ---
        if self.mode == self.MODE_LATCH and not self._mute_held and self._drum_zone and msg.is_note_on:
            if self._drum_zone.contains(msg.note):
                row, col = self._drum_zone.index_of(msg.note)
                pad_index = row * self._drum_zone.width + col
                self._toggle_mute(pad_index)
                return True

        return False

    # ------------------------------------------------------------------
    # Mode toggle (also callable externally)
    # ------------------------------------------------------------------

    def toggle_mode(self):
        if self.mode == self.MODE_MOMENTARY:
            self.mode = self.MODE_LATCH
            self._pending_mutes.clear()
            self._mute_held = False
            self._refresh_pad_states()
            self.adapter.set_pad_pulse(PAD_MUTE_BUTTON, COLOR_LATCH_ACTIVE)
        else:
            self.mode = self.MODE_MOMENTARY
            self._pending_mutes.clear()
            self._mute_held = False
            self._refresh_pad_states()
            self.adapter.clear_pad(PAD_MUTE_BUTTON)

    # ------------------------------------------------------------------
    # Mute operations
    # ------------------------------------------------------------------

    def _toggle_mute(self, pad_index: int):
        chain = self._chain_for_index(pad_index)
        if chain is not None:
            chain.mute = not chain.mute
        self._refresh_pad_states()

    def _apply_mutes(self):
        """Commit all staged (pending) mute toggles."""
        for pad_index in self._pending_mutes:
            chain = self._chain_for_index(pad_index)
            if chain is not None:
                chain.mute = not chain.mute

    def _chain_for_index(self, pad_index: int):
        """Return Live.DrumChain for pad_index on the selected track, or None."""
        try:
            track = self.song.view.selected_track
            for device in track.devices:
                if hasattr(device, "chains"):
                    chains = list(device.chains)
                    if pad_index < len(chains):
                        return chains[pad_index]
        except Exception:
            pass
        return None

    # ------------------------------------------------------------------
    # LED refresh
    # ------------------------------------------------------------------

    def _refresh_pad_states(self):
        if self._drum_zone is None:
            return
        for idx, pad in enumerate(self._drum_zone.pads):
            chain = self._chain_for_index(idx)
            if chain is None:
                self.adapter.clear_pad(pad)
                continue

            muted   = getattr(chain, "mute", False)
            pending = idx in self._pending_mutes

            if self.mode == self.MODE_LATCH and pending:
                # Staged for commit: green pulse
                self.adapter.set_pad_pulse(pad, COLOR_STAGED)
            elif muted:
                # Muted: grey
                self.adapter.set_pad_palette(pad, COLOR_MUTED)
            elif self.mode == self.MODE_LATCH:
                # Armed, not staged, in latch → fondu clignotant per spec
                self.adapter.set_pad_pulse(pad, COLOR_ARMED_PULSE)
            else:
                self.adapter.clear_pad(pad)

    # ------------------------------------------------------------------
    # State snapshot
    # ------------------------------------------------------------------

    def snapshot(self) -> dict:
        return {
            "mute_mode": self.mode,
        }
