"""
LPX95Custom — Root ControlSurface class for the Novation Launchpad X custom script.

This file runs inside Ableton's Python sandbox. All imports are stdlib or Ableton APIs.
"""

import os

# Ableton APIs (available only when running inside Ableton)
import Live
from _Framework.ControlSurface import ControlSurface

from material.launchpad_x import LaunchpadXAdapter
from behaviors.router import BehaviorRouter
from behaviors.drum_pad import DrumPadBehavior
from behaviors.step_sequencer import StepSequencerBehavior
from behaviors.trigger_roll import TriggerRollBehavior
from behaviors.mute_mode import MuteModeBehavior
from behaviors.lock_mode import LockModeBehavior
from state_writer import StateWriter
from protocol.midi import parse


def _script_dir() -> str:
    """Locate this file's directory without relying on __file__."""
    import inspect
    return os.path.dirname(os.path.realpath(inspect.getfile(lambda: 0)))


class LPX95Custom(ControlSurface):

    def __init__(self, c_instance):
        super().__init__(c_instance)
        with self.component_guard():
            self._setup()

    def _setup(self):
        base = _script_dir()
        config_path = os.path.join(base, "configs", "devices", "launchpad_x.json")
        state_path  = os.path.join(os.path.expanduser("~"), ".lpx95", "state.json")

        state_writer    = StateWriter(state_path)
        self._adapter   = LaunchpadXAdapter(self._send_midi, config_path)
        self._adapter.enter_programmer_mode()

        song = self.song()

        seq  = StepSequencerBehavior(self._adapter, song)
        drum = DrumPadBehavior(self._adapter, song, seq)
        roll = TriggerRollBehavior(self._adapter, song)
        mute = MuteModeBehavior(self._adapter, song)
        lock = LockModeBehavior(self._adapter, song)

        # Give lock mode a reference so it can auto-switch the sequencer
        lock._sequencer_ref = seq

        self._router = BehaviorRouter(self._adapter, song, state_writer)
        # Push in reverse priority order — last pushed = first to receive MIDI
        self._router.push(lock)
        self._router.push(mute)
        self._router.push(drum)
        self._router.push(seq)   # top of stack; highest priority

    # ------------------------------------------------------------------
    # Ableton callbacks
    # ------------------------------------------------------------------

    def receive_midi_chunk(self, midi_bytes):
        for status, d1, d2 in midi_bytes:
            self._router.dispatch(parse(status, d1, d2))

    def disconnect(self):
        self._adapter.clear_all()
        self._adapter.exit_programmer_mode()
        super().disconnect()
