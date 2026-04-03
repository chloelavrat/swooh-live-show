"""
LockModeBehavior — track/clip lock state machine.

States cycled via toggle press:
  UNLOCKED → LOCK_TRACK → FULL_LOCK → UNLOCKED

UNLOCKED:    All nav arrows active (white). Follows session view.
LOCK_TRACK:  Left/Right arrows greyed. Locks to selected track.
FULL_LOCK:   All arrows greyed. Locks to track + clip;
             auto-switches sequencer on clip trigger (polled each tick).
"""

from .base import BaseBehavior
from protocol.constants import (
    PAD_LOCK_TOGGLE,
    CC_NAV_UP, CC_NAV_DOWN, CC_NAV_LEFT, CC_NAV_RIGHT,
)

# Novation palette indices
COLOR_UNLOCKED   = 48   # dim violet
COLOR_LOCK_TRACK = 49   # bright violet
COLOR_FULL_LOCK  = 49   # used with pulse for full_lock
COLOR_NAV_ACTIVE = 3    # bright white
COLOR_NAV_GRAYED = 1    # dark grey

STATES = ["unlocked", "lock_track", "full_lock"]


class LockModeBehavior(BaseBehavior):

    def __init__(self, adapter, song):
        super().__init__(adapter, song)
        self._state         = "unlocked"
        self._locked_track  = None
        self._locked_clip   = None
        self._sequencer_ref = None   # set externally if auto-switch needed

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def on_enter(self):
        self._update_nav_leds()

    def on_exit(self):
        self.adapter.clear_pad(PAD_LOCK_TOGGLE)
        # Restore nav arrows to default (clear so hardware reverts to its own display)
        for cc in (CC_NAV_UP, CC_NAV_DOWN, CC_NAV_LEFT, CC_NAV_RIGHT):
            self.adapter.clear_pad(cc)

    # ------------------------------------------------------------------
    # MIDI handling
    # ------------------------------------------------------------------

    def handle_midi(self, msg) -> bool:
        # Lock toggle pad
        if msg.is_note_on and msg.note == PAD_LOCK_TOGGLE:
            self.cycle()
            return True

        # Intercept nav arrows when locked
        if msg.is_cc:
            if self._state in ("lock_track", "full_lock"):
                if msg.cc_number in (CC_NAV_LEFT, CC_NAV_RIGHT):
                    return True   # consume — blocked
            if self._state == "full_lock":
                if msg.cc_number in (CC_NAV_UP, CC_NAV_DOWN):
                    return True   # consume — blocked

        return False

    # ------------------------------------------------------------------
    # Tick — poll for clip changes in full_lock
    # ------------------------------------------------------------------

    def tick(self):
        if self._state != "full_lock" or self._locked_track is None:
            return
        try:
            for slot in self._locked_track.clip_slots:
                if slot.clip is not None and slot.clip.is_playing:
                    if slot.clip is not self._locked_clip:
                        self._on_clip_triggered(slot.clip)
                    break
        except Exception:
            pass

    # ------------------------------------------------------------------
    # State machine
    # ------------------------------------------------------------------

    def cycle(self):
        current_idx = STATES.index(self._state)
        self._state = STATES[(current_idx + 1) % len(STATES)]

        if self._state == "lock_track":
            self._lock_to_track()
        elif self._state == "full_lock":
            self._lock_to_clip()
        else:
            self._locked_track = None
            self._locked_clip  = None

        self._update_nav_leds()

    def _lock_to_track(self):
        try:
            self._locked_track = self.song.view.selected_track
        except Exception:
            self._locked_track = None

    def _lock_to_clip(self):
        self._lock_to_track()
        try:
            for slot in self._locked_track.clip_slots:
                if slot.clip is not None and slot.clip.is_playing:
                    self._locked_clip = slot.clip
                    return
            # Fallback: first clip
            for slot in self._locked_track.clip_slots:
                if slot.clip is not None:
                    self._locked_clip = slot.clip
                    return
        except Exception:
            pass
        self._locked_clip = None

    # ------------------------------------------------------------------
    # LED update
    # ------------------------------------------------------------------

    def _update_nav_leds(self):
        if self._state == "unlocked":
            self.adapter.set_pad_palette(PAD_LOCK_TOGGLE, COLOR_UNLOCKED)
            for cc in (CC_NAV_UP, CC_NAV_DOWN, CC_NAV_LEFT, CC_NAV_RIGHT):
                self.adapter.set_pad_palette(cc, COLOR_NAV_ACTIVE)
        elif self._state == "lock_track":
            self.adapter.set_pad_palette(PAD_LOCK_TOGGLE, COLOR_LOCK_TRACK)
            # Up/Down active, Left/Right grayed
            self.adapter.set_pad_palette(CC_NAV_UP,    COLOR_NAV_ACTIVE)
            self.adapter.set_pad_palette(CC_NAV_DOWN,  COLOR_NAV_ACTIVE)
            self.adapter.set_pad_palette(CC_NAV_LEFT,  COLOR_NAV_GRAYED)
            self.adapter.set_pad_palette(CC_NAV_RIGHT, COLOR_NAV_GRAYED)
        else:  # full_lock
            self.adapter.set_pad_pulse(PAD_LOCK_TOGGLE, COLOR_FULL_LOCK)
            for cc in (CC_NAV_UP, CC_NAV_DOWN, CC_NAV_LEFT, CC_NAV_RIGHT):
                self.adapter.set_pad_palette(cc, COLOR_NAV_GRAYED)

    # ------------------------------------------------------------------
    # Clip trigger callback
    # ------------------------------------------------------------------

    def _on_clip_triggered(self, clip):
        """Auto-switch sequencer to the triggered clip in full_lock."""
        if self._state == "full_lock" and self._sequencer_ref is not None:
            self._sequencer_ref.set_clip(clip)
            self._locked_clip = clip

    # ------------------------------------------------------------------
    # State snapshot
    # ------------------------------------------------------------------

    def snapshot(self) -> dict:
        return {"lock_state": self._state}
