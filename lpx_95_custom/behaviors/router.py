"""
BehaviorRouter — dispatches MIDI to the active behavior stack.

Stack discipline:
  - push(behavior)   → calls on_enter(); behavior receives MIDI first.
  - pop()            → calls on_exit() on top behavior.
  - dispatch(msg)    → walks stack top→bottom; stops when a behavior returns True.
  - tick()           → forwards to all registered behaviors.
  - snapshot()       → assembles full state dict from all behaviors + song.
"""

import time


class BehaviorRouter:

    def __init__(self, adapter, song, state_writer=None):
        self.adapter       = adapter
        self.song          = song
        self._stack        = []          # list of BaseBehavior, index -1 = top
        self._state_writer = state_writer
        self._last_snapshot_hash = None

    # ------------------------------------------------------------------
    # Stack management
    # ------------------------------------------------------------------

    def push(self, behavior):
        """Activate a new behavior on top of the stack."""
        self._stack.append(behavior)
        behavior.on_enter()

    def pop(self):
        """Deactivate and remove the top behavior."""
        if self._stack:
            behavior = self._stack.pop()
            behavior.on_exit()
            return behavior
        return None

    def replace_top(self, behavior):
        """Pop the current top and push a new one atomically."""
        self.pop()
        self.push(behavior)

    # ------------------------------------------------------------------
    # MIDI dispatch
    # ------------------------------------------------------------------

    def dispatch(self, msg):
        """Walk stack top→bottom; first behavior returning True consumes the message."""
        for behavior in reversed(self._stack):
            if behavior.handle_midi(msg):
                break
        self._maybe_write_state()

    # ------------------------------------------------------------------
    # Tick
    # ------------------------------------------------------------------

    def tick(self):
        """Forward tick to all behaviors in stack order (bottom first)."""
        for behavior in self._stack:
            behavior.tick()
        self._maybe_write_state()

    # ------------------------------------------------------------------
    # State serialization
    # ------------------------------------------------------------------

    def snapshot(self) -> dict:
        """
        Assemble a full state dict by merging snapshots from all behaviors.
        Also includes song-level fields (BPM, playhead, is_playing).
        """
        state = {
            "version":        1,
            "ts":             time.time(),
            "bpm":            120.0,
            "is_playing":     False,
            "playhead_beat":  0.0,
            "lock_state":     "unlocked",
            "active_mode":    "step_sequencer",
            "drum_pads":      [],
            "step_grid": {
                "clip_length_beats":  0.0,
                "scroll_offset_steps": 0,
                "steps":              [],
            },
        }

        # Song-level fields
        try:
            state["bpm"]           = float(self.song.tempo)
            state["is_playing"]    = bool(self.song.is_playing)
            state["playhead_beat"] = float(self.song.current_song_time)
        except Exception:
            pass

        # Merge behavior snapshots
        for behavior in self._stack:
            try:
                partial = behavior.snapshot()
                state.update(partial)
            except Exception:
                pass

        return state

    def _maybe_write_state(self):
        if self._state_writer is None:
            return
        state = self.snapshot()
        # Simple hash to skip writes if nothing changed
        import json
        h = hash(json.dumps(state, sort_keys=True, default=str))
        if h != self._last_snapshot_hash:
            self._last_snapshot_hash = h
            self._state_writer.write(state)
