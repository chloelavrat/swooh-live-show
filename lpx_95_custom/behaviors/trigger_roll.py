"""
TriggerRollBehavior — momentary trigger-roll mode.

While the Trigger Roll pad is held:
  - The clip_length row is replaced with a quantize submenu (3 options).
  - Holding Trigger Roll + any drum pad fires repeated notes at the selected subdivision.
  - Uses _Framework.Task for scheduling when running inside Ableton.
  - Falls back to a simple tick-based counter for testing outside Ableton.
"""

from .base import BaseBehavior
from protocol.constants import PAD_TRIGGER_ROLL

# Quantize options
QUANTIZE_OPTIONS = {
    "1/4":  1.0,
    "1/8":  0.5,
    "1/16": 0.25,
}
DEFAULT_QUANTIZE = "1/16"

# Palette colors for submenu pads
COLOR_Q_ACTIVE   = 5   # red — currently selected
COLOR_Q_INACTIVE = 1   # dim grey
COLOR_OFF        = 0


class TriggerRollBehavior(BaseBehavior):

    def __init__(self, adapter, song):
        super().__init__(adapter, song)
        self._active         = False           # True while Trigger Roll pad held
        self._roll_note      = None            # note currently rolling
        self._roll_velocity  = 100
        self._quantize_key   = DEFAULT_QUANTIZE
        self._roll_task      = None
        self._ticks_per_beat = 24              # MIDI clock ppq approximation
        self._tick_counter   = 0
        self._nav_zone       = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def on_enter(self):
        try:
            self._nav_zone = self.adapter.zone("clip_length")
        except KeyError:
            self._nav_zone = None

    def on_exit(self):
        self._stop_roll()
        self._hide_quantize_menu()

    # ------------------------------------------------------------------
    # MIDI handling
    # ------------------------------------------------------------------

    def handle_midi(self, msg) -> bool:
        # Trigger Roll pad press
        if msg.is_note_on and msg.note == PAD_TRIGGER_ROLL:
            self._active = True
            self._show_quantize_menu()
            return True

        # Trigger Roll pad release
        if msg.is_note_off and msg.note == PAD_TRIGGER_ROLL:
            self._active = False
            self._stop_roll()
            self._hide_quantize_menu()
            return True

        # Quantize selection while held
        if self._active and self._nav_zone and msg.is_note_on:
            if self._nav_zone.contains(msg.note):
                idx = self._nav_zone.pads.index(msg.note)
                keys = list(QUANTIZE_OPTIONS.keys())
                if idx < len(keys):
                    self._quantize_key = keys[idx]
                    self._show_quantize_menu()
                return True

        # Drum pad roll while Trigger Roll held
        if self._active and msg.is_note_on:
            self._start_roll(msg.note, msg.data2)
            return True

        if self._active and msg.is_note_off:
            if msg.note == self._roll_note:
                self._stop_roll()
            return True

        return False

    # ------------------------------------------------------------------
    # Roll scheduling
    # ------------------------------------------------------------------

    def _start_roll(self, note: int, velocity: int = 100):
        self._stop_roll()
        self._roll_note     = note
        self._roll_velocity = velocity

        # Try to use _Framework.Task if available (inside Ableton)
        try:
            from _Framework.Task import Task
            interval = QUANTIZE_OPTIONS[self._quantize_key]

            def fire():
                self._fire_note()

            self._roll_task = self.song._tasks.add(
                Task.loop(Task.delay(interval), Task.run(fire))
            )
        except Exception:
            # Outside Ableton: tick-based fallback (driven by self.tick())
            self._roll_task = "tick_fallback"
            self._tick_counter = 0

    def _stop_roll(self):
        if self._roll_task and self._roll_task != "tick_fallback":
            try:
                self._roll_task.kill()
            except Exception:
                pass
        self._roll_task  = None
        self._roll_note  = None
        self._tick_counter = 0

    def _fire_note(self):
        if self._roll_note is None:
            return
        self.adapter.send_note_on(self._roll_note, self._roll_velocity)

    # ------------------------------------------------------------------
    # Tick-based fallback (used outside Ableton / in tests)
    # ------------------------------------------------------------------

    def tick(self):
        if self._roll_task != "tick_fallback":
            return
        try:
            bpm      = self.song.tempo
        except Exception:
            bpm      = 120.0
        beats_per_tick = bpm / (60.0 * self._ticks_per_beat)
        interval_beats = QUANTIZE_OPTIONS[self._quantize_key]
        ticks_needed   = int(interval_beats / beats_per_tick)

        self._tick_counter += 1
        if ticks_needed > 0 and self._tick_counter >= ticks_needed:
            self._tick_counter = 0
            self._fire_note()

    # ------------------------------------------------------------------
    # Quantize menu drawing
    # ------------------------------------------------------------------

    def _show_quantize_menu(self):
        if self._nav_zone is None:
            return
        keys = list(QUANTIZE_OPTIONS.keys())
        for i, pad in enumerate(self._nav_zone.pads):
            if i < len(keys):
                color = COLOR_Q_ACTIVE if keys[i] == self._quantize_key else COLOR_Q_INACTIVE
                self.adapter.set_pad_palette(pad, color)
            else:
                self.adapter.clear_pad(pad)

    def _hide_quantize_menu(self):
        if self._nav_zone is None:
            return
        for pad in self._nav_zone.pads:
            self.adapter.clear_pad(pad)

    # ------------------------------------------------------------------
    # State snapshot
    # ------------------------------------------------------------------

    def snapshot(self) -> dict:
        return {
            "trigger_roll_active":  self._active,
            "trigger_roll_quantize": self._quantize_key,
        }
