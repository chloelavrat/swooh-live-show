#!/usr/bin/env python3
"""
LPX95 Fake Controller Simulator
================================
Runs the full behavior stack (no Ableton, no hardware) and exposes an HTTP API
so the Control Room frontend can fire MIDI events by clicking pads.

Usage:
    python3 lpx_95_custom/scripts/simulator.py

API (port 9002):
    POST /midi    body: {"status": 0x90, "data1": 36, "data2": 100}
    GET  /health  → 200 OK
"""

import sys
import os
import json
import time
import threading

from http.server import HTTPServer, BaseHTTPRequestHandler

# ── Path setup ────────────────────────────────────────────────────────────────
SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)   # lpx_95_custom/
sys.path.insert(0, PROJECT_ROOT)

# Inject Ableton stubs before any behavior import
from tests.mocks.framework_mock import MockAdapter  # noqa — injects Live/_Framework stubs
from tests.mocks.live_mock import (
    MockSong, MockDrumChain, MockDevice,
    MockTrack, MockView, MockClip, MockClipSlot,
)

from behaviors.router import BehaviorRouter
from behaviors.drum_pad import DrumPadBehavior
from behaviors.step_sequencer import StepSequencerBehavior
from behaviors.trigger_roll import TriggerRollBehavior
from behaviors.mute_mode import MuteModeBehavior
from behaviors.lock_mode import LockModeBehavior
from state_writer import StateWriter
from protocol.midi import parse
from material.color import NOVATION_COLORS

# ── Config ────────────────────────────────────────────────────────────────────
PORT        = int(os.environ.get("SIMULATOR_PORT", "9002"))
CONFIG_PATH = os.path.join(PROJECT_ROOT, "configs", "devices", "launchpad_x.json")
STATE_PATH  = os.path.join(os.path.expanduser("~"), ".lpx95", "state.json")
TICK_INTERVAL = 0.05   # seconds between song-time ticks (50 ms ≈ 20 Hz)


# ── SimulatorAdapter ──────────────────────────────────────────────────────────

class SimulatorAdapter(MockAdapter):
    """
    Extends MockAdapter to capture LED state so it can be included in state.json.
    LED state is stored as {pad_note: [r, g, b]} and written to state.json by
    SimulatorRouter.snapshot().
    """

    def __init__(self, config_path):
        super().__init__(config_path=config_path)
        self._leds: dict = {}   # pad_note (int) → [r, g, b]

    def _palette_rgb(self, index: int):
        if 0 <= index < len(NOVATION_COLORS):
            return list(NOVATION_COLORS[index])
        return [0, 0, 0]

    def set_pad_rgb(self, pad, r, g, b):
        super().set_pad_rgb(pad, r, g, b)
        self._leds[pad] = [r & 0x7F, g & 0x7F, b & 0x7F]

    def set_pad_palette(self, pad, color_index):
        super().set_pad_palette(pad, color_index)
        self._leds[pad] = self._palette_rgb(color_index)

    def set_pad_pulse(self, pad, color_index):
        super().set_pad_pulse(pad, color_index)
        self._leds[pad] = self._palette_rgb(color_index)

    def set_pad_flash(self, pad, color_a, color_b):
        super().set_pad_flash(pad, color_a, color_b)
        # Show color_a; flash can't be rendered as static JSON
        self._leds[pad] = self._palette_rgb(color_a)

    def clear_pad(self, pad):
        super().clear_pad(pad)
        self._leds[pad] = [0, 0, 0]

    def clear_all(self):
        super().clear_all()
        self._leds.clear()

    def bulk_set_rgb(self, updates):
        super().bulk_set_rgb(updates)
        for pad, r, g, b in updates:
            self._leds[pad] = [r, g, b]

    def leds_snapshot(self) -> dict:
        return {str(k): v for k, v in self._leds.items()}


# ── SimulatorRouter ───────────────────────────────────────────────────────────

class SimulatorRouter(BehaviorRouter):
    """Extends BehaviorRouter.snapshot() to include LED state."""

    def snapshot(self) -> dict:
        state = super().snapshot()
        state["leds"] = self.adapter.leds_snapshot()
        return state


# ── Song / track setup ────────────────────────────────────────────────────────

def build_song() -> MockSong:
    song = MockSong()
    song.tempo      = 120.0
    song.is_playing = True

    chains = [
        MockDrumChain("Kick",   36, 5,  False),
        MockDrumChain("Snare",  38, 21, False),
        MockDrumChain("HiHat",  42, 9,  False),
        MockDrumChain("Clap",   39, 48, False),
        MockDrumChain("Open HH",46, 12, False),
        MockDrumChain("Ride",   51, 17, False),
        MockDrumChain("Crash",  49, 5,  False),
        MockDrumChain("Perc",   47, 30, False),
    ]
    device = MockDevice(chains=chains)

    # Pre-populate a simple 4-beat clip with a kick pattern
    clip = MockClip(loop_end=4.0)
    for beat in range(4):
        clip.set_notes(((36, float(beat), 0.2, 100, False),))   # kick on beats 1–4
    clip.set_notes(((38, 1.0, 0.2, 90, False),))                # snare on beat 2
    clip.set_notes(((38, 3.0, 0.2, 90, False),))                # snare on beat 4

    track  = MockTrack(device=device, clips=[MockClipSlot(clip)])
    song.view = MockView(track=track)
    return song


# ── Main simulator setup ──────────────────────────────────────────────────────

_adapter = SimulatorAdapter(CONFIG_PATH)
_song    = build_song()
_writer  = StateWriter(STATE_PATH)
_router  = SimulatorRouter(_adapter, _song, _writer)

# Boot behavior stack
_seq  = StepSequencerBehavior(_adapter, _song)
_drum = DrumPadBehavior(_adapter, _song, _seq)
_roll = TriggerRollBehavior(_adapter, _song)
_mute = MuteModeBehavior(_adapter, _song)
_lock = LockModeBehavior(_adapter, _song)
_lock._sequencer_ref = _seq

# Wire the initial clip to the sequencer
_initial_clip = _song.view.selected_track.clip_slots[0].clip
_seq.set_clip(_initial_clip)

_router.push(_lock)
_router.push(_mute)
_router.push(_drum)
_router.push(_seq)

# ── Song-time ticker ──────────────────────────────────────────────────────────

def _run_ticker():
    """Advance song time at a fixed rate, simulating playback."""
    while True:
        time.sleep(TICK_INTERVAL)
        bpm = _song.tempo
        _song.current_song_time += (bpm / 60.0) * TICK_INTERVAL
        for fn in list(_song._song_time_listeners):
            try:
                fn()
            except Exception:
                pass
        _router.tick()


_ticker = threading.Thread(target=_run_ticker, daemon=True)
_ticker.start()


# ── HTTP server ───────────────────────────────────────────────────────────────

class SimHandler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        if self.path == "/health":
            self._json({"ok": True, "bpm": _song.tempo, "time": _song.current_song_time})
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/midi":
            length = int(self.headers.get("Content-Length", "0"))
            body   = self.rfile.read(length)
            try:
                data = json.loads(body)
                msg  = parse(int(data["status"]), int(data["data1"]), int(data["data2"]))
                _router.dispatch(msg)
                self._json({"ok": True})
            except Exception as exc:
                self.send_response(400)
                self._cors()
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(exc)}).encode())
        elif self.path == "/tempo":
            length = int(self.headers.get("Content-Length", "0"))
            body   = self.rfile.read(length)
            try:
                data = json.loads(body)
                _song.tempo = float(data["bpm"])
                self._json({"ok": True, "bpm": _song.tempo})
            except Exception as exc:
                self.send_response(400)
                self._cors()
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(exc)}).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def _json(self, payload: dict):
        self.send_response(200)
        self._cors()
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode())

    def _cors(self):
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def log_message(self, fmt, *args):
        # Suppress per-request logging; only log errors
        if args and str(args[1]) not in ("200", "204"):
            print(f"[simulator] {fmt % args}")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    HTTPServer.allow_reuse_address = True
    server = HTTPServer(("localhost", PORT), SimHandler)
    print(f"[simulator] HTTP server on http://localhost:{PORT}")
    print(f"[simulator] Writing state to {STATE_PATH}")
    print(f"[simulator] Song: {_song.tempo} BPM, {len(_song.view.selected_track.devices[0].chains)} chains")
    print(f"[simulator] Press Ctrl-C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[simulator] Stopped.")
