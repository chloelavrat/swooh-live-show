# LPX_95_Custom — Claude Code Build Specification

> **Standalone build document for Claude Code.**  
> Target: Novation Launchpad X × Ableton Live MIDI Remote Script  
> Language: Python 3.x (constrained to Ableton's embedded runtime)  
> Architecture: 4-layer — Protocol / Behaviors / Material / Control Room UI

---

## 1. Project Overview

LPX_95_Custom is a custom Ableton Live MIDI Remote Script for the Novation Launchpad X. It replaces the stock script with a fully programmable drum sequencer surface: step sequencing, drum pad selection, playhead tracking, trigger roll, and mute modes — all driven by SysEx LED feedback and configurable via YAML device/behavior files.

The architecture is designed to be controller-agnostic at the material layer: swapping in a different controller (Push, APC, etc.) requires only a new YAML device file and adapter class.

A fourth layer — the **Control Room UI** — provides a read-only, browser-based view of the sequencer state for on-stage monitoring. It receives live state via a lightweight WebSocket bridge (companion process, outside Ableton's sandbox) and renders it as a minimalist dashboard. No configuration is possible from the UI; it is a passive mirror of what the hardware is doing.

---

## 2. Hard Constraints

| Constraint | Detail |
|---|---|
| **Python runtime** | Ableton embeds Python 3.x (varies by version; target 3.9+). No pip, no venv. Stdlib only + Ableton's `Live` C-extension. |
| **No asyncio** | Use `_Framework.Task` / `LiveThread` for deferred/periodic execution. |
| **No external processes** | Everything runs inside Ableton's Remote Script sandbox. |
| **MIDI I/O** | `send_midi(tuple)` for output; `receive_midi_chunk` / `_receive_midi` for input — no `mido` or `rtmidi`. |
| **SysEx framing** | Ableton strips `0xF0`/`0xF7` from received SysEx. Strip them on send too when using `send_midi`. Novation SysEx header: `[0x00, 0x20, 0x29, 0x02, 0x0C]`. |
| **YAML parsing** | PyYAML is not available. Use the stdlib `json` module OR vendor a minimal YAML parser. **Preferred: convert YAML configs to JSON at install time via a helper script.** |
| **No `__file__`** | Use `os.path.dirname(os.path.realpath(__import__('inspect').getfile(lambda:0)))` to locate the script directory. |

---

## 3. File Structure

```
lpx_95_custom/
│
├── __init__.py                  # Ableton entry point — exposes create_instance()
├── LPX95Custom.py               # Root controller class (ControlSurface subclass)
│
├── protocol/                    # Layer 1 — MIDI & SysEx codec
│   ├── __init__.py
│   ├── midi.py                  # MidiMessage dataclass, note/CC parsers
│   ├── sysex.py                 # SysEx encoder/decoder, Novation command builders
│   └── constants.py             # SysEx headers, note numbers, CC map
│
├── behaviors/                   # Layer 2 — Mode state machines
│   ├── __init__.py
│   ├── base.py                  # BaseBehavior ABC: handle_midi(), on_enter(), on_exit()
│   ├── drum_pad.py              # DrumPadBehavior: 4×4 chain selector
│   ├── step_sequencer.py        # StepSequencerBehavior: note grid + playhead
│   ├── trigger_roll.py          # TriggerRollBehavior: timed note injection
│   ├── mute_mode.py             # MuteModeBehavior: momentary + latch FSM
│   ├── lock_mode.py             # LockModeBehavior: piste / full lock
│   └── router.py                # BehaviorRouter: dispatches MIDI → active behavior
│
├── material/                    # Layer 3 — Device abstraction
│   ├── __init__.py
│   ├── base_adapter.py          # DeviceAdapter ABC
│   ├── launchpad_x.py           # LaunchpadXAdapter: zone resolver, LED commands
│   ├── zone.py                  # Zone dataclass: grid region → pad note mapping
│   └── color.py                 # ColorMapper: Ableton color index → Novation palette
│
├── configs/                     # YAML source files (converted to JSON at install)
│   ├── devices/
│   │   └── launchpad_x.yaml     # Device geometry, CC map, SysEx palette
│   └── behaviors/
│       └── drum_sequencer.yaml  # Zone bindings, mode defaults, color rules
│
├── scripts/                     # Developer tooling (runs outside Ableton)
│   ├── convert_configs.py       # YAML → JSON converter (run before install)
│   └── install.py               # Copies script to Ableton's Remote Scripts dir
│
└── tests/                       # Offline unit tests (no Ableton dependency)
    ├── test_sysex.py
    ├── test_zone.py
    ├── test_step_sequencer.py
    └── test_color_mapper.py

control_room/                        # Layer 4 — Control Room UI (React + Vite)
│
├── index.html
├── vite.config.ts
├── tailwind.config.ts
├── postcss.config.js
├── package.json
│
├── src/
│   ├── main.tsx                     # React entry point; mounts App
│   ├── App.tsx                      # Root: theme provider, WebSocket hook, layout
│   │
│   ├── hooks/
│   │   └── useSequencerState.ts     # WebSocket subscriber → returns SequencerState
│   │
│   ├── types/
│   │   └── state.ts                 # TypeScript types mirroring bridge state schema
│   │
│   └── components/
│       ├── StepGrid.tsx             # 8×8 read-only step grid
│       ├── DrumPads.tsx             # 4×4 pad grid with chain colors + mute badges
│       ├── StatusBar.tsx            # BPM · lock state · active mode · connection dot
│       └── Playhead.tsx             # Current beat / clip position indicator
│
└── bridge/                          # Companion server (runs outside Ableton)
    ├── server.ts                    # Node.js: watches state file → broadcasts WS
    └── schema.ts                    # State schema (shared source of truth with src/types)
```

---

## 4. Layer 1 — Protocol

### 4.1 `protocol/constants.py`

```python
NOVATION_SYSEX_HEADER = (0x00, 0x20, 0x29, 0x02, 0x0C)

# Programmer mode on/off
PROGRAMMER_MODE_ON  = NOVATION_SYSEX_HEADER + (0x0E, 0x01)
PROGRAMMER_MODE_OFF = NOVATION_SYSEX_HEADER + (0x0E, 0x00)

# Pad note layout: bottom-left = 11, row-major, 9-wide grid
PAD_OFFSET = 11
GRID_WIDTH  = 9

# CC numbers (channel 1, 0-indexed = channel 0 in code)
CC_OCTAVE_UP   = 89
CC_OCTAVE_DOWN = 79
CC_NAV_UP      = 91
CC_NAV_DOWN    = 92
CC_NAV_LEFT    = 93
CC_NAV_RIGHT   = 94
```

### 4.2 `protocol/sysex.py`

Implement the following functions. All return `tuple[int, ...]` for direct use with `send_midi()`.

```python
def set_led_rgb(pad: int, r: int, g: int, b: int) -> tuple:
    """SysEx: F0 00 20 29 02 0C 03 03 <pad> <r> <g> <b> F7"""

def set_led_palette(pad: int, color_index: int) -> tuple:
    """SysEx: F0 00 20 29 02 0C 03 00 <pad> <color> F7"""

def set_led_flash(pad: int, color_a: int, color_b: int) -> tuple:
    """SysEx: F0 00 20 29 02 0C 03 01 <pad> <color_a> <color_b> F7"""

def set_led_pulse(pad: int, color_index: int) -> tuple:
    """SysEx: F0 00 20 29 02 0C 03 02 <pad> <color> F7"""

def bulk_led_rgb(updates: list[tuple[int, int, int, int]]) -> tuple:
    """Batch LED update: list of (pad, r, g, b). Single SysEx message."""

def programmer_mode(on: bool) -> tuple:
    """Switch Launchpad X between Live mode and Programmer mode."""
```

> **Note on Ableton's SysEx stripping**: when sending, include `0xF0` and `0xF7` in the tuple. When receiving, Ableton delivers the payload without framing bytes — account for this in the decoder.

### 4.3 `protocol/midi.py`

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class MidiMessage:
    status: int       # raw status byte
    data1: int
    data2: int

    @property
    def channel(self) -> int: ...
    @property
    def is_note_on(self) -> bool: ...
    @property
    def is_note_off(self) -> bool: ...
    @property
    def is_cc(self) -> bool: ...
    @property
    def is_sysex(self) -> bool: ...

def parse(status: int, data1: int, data2: int) -> MidiMessage: ...
```

---

## 5. Layer 2 — Behaviors

### 5.1 `behaviors/base.py`

```python
from abc import ABC, abstractmethod
from protocol.midi import MidiMessage

class BaseBehavior(ABC):
    def __init__(self, adapter, song):
        self.adapter = adapter   # DeviceAdapter instance
        self.song = song         # Live.Song.Song

    @abstractmethod
    def on_enter(self): ...      # Called when mode becomes active; draw initial state

    @abstractmethod
    def on_exit(self): ...       # Called when mode deactivated; clear LEDs

    @abstractmethod
    def handle_midi(self, msg: MidiMessage) -> bool:
        """Return True if message was consumed, False to pass through."""
        ...

    def tick(self):
        """Called on each scheduler tick (if registered). Optional."""
        pass
```

### 5.2 `behaviors/drum_pad.py` — DrumPadBehavior

**Responsibilities:**
- Map the 4×4 pad zone (bottom-left of grid) to Drum Rack chains (C1–D#2 by default)
- On pad press: select corresponding chain in Ableton; update StepSequencer target
- On chain color change: update LED via `adapter.set_pad_color(pad, color)`
- Octave shift (CC 89/79): shift the 16-pad window up/down by 16 notes
- LED state rules:
  - **Colored** (chain color): pad armed
  - **Red**: note currently playing (playhead pass)
  - **Grey**: pad muted
  - **Black (off)**: empty

```python
class DrumPadBehavior(BaseBehavior):
    ZONE = "drum_pad"           # references device YAML zone key
    DEFAULT_ROOT_NOTE = 36      # C1

    def __init__(self, adapter, song, sequencer_ref):
        super().__init__(adapter, song)
        self.root_note = self.DEFAULT_ROOT_NOTE
        self.sequencer = sequencer_ref  # back-reference for chain selection

    def _chain_for_pad(self, pad_index: int) -> Optional[Live.DrumChain.DrumChain]: ...
    def _refresh_all_leds(self): ...
    def _on_chain_color_changed(self): ...  # Live API listener
```

### 5.3 `behaviors/step_sequencer.py` — StepSequencerBehavior

**Responsibilities:**
- Display a 1/16-grid view of the selected Drum Rack chain's MIDI clip
- Grid is 8×8 (8 bars × 8 steps per bar = 64 steps of 1/16)
- Navigation: horizontal scrolling through clip via clip-length row (row 8)
- Playhead: orange LED advances step-by-step; driven by `song.current_song_time` listener
- On empty pad press: insert note at velocity 100
- On filled pad press: delete note
- LED brightness encodes velocity (0–127 → dim green to bright green)
- Muted notes: grey; playing + muted: slow red pulse

```python
class StepSequencerBehavior(BaseBehavior):
    ZONE = "step_sequencer"
    STEP_LENGTH = 0.25          # 1/16 in beats (1 beat = 1/4 note)
    GRID_COLS   = 8
    GRID_ROWS   = 8

    def __init__(self, adapter, song):
        super().__init__(adapter, song)
        self.clip = None         # currently watched Live.Clip
        self.scroll_offset = 0   # in steps
        self._playhead_step = 0

    def set_clip(self, clip): ...           # switch watched clip, redraw
    def _steps_in_view(self) -> list: ...  # returns list of (beat_time, note|None)
    def _draw_grid(self): ...
    def _on_song_time_changed(self): ...   # listener → update playhead LED
    def _velocity_to_color(self, velocity: int) -> int: ...  # → palette index
```

**Clip length row (row 8):**
- 1 pad = 1 beat. Lit = clip has content there. Bright = currently visible window.
- Pressing a pad scrolls the grid view to that beat.
- Clip length is **read-only** — no resize.

### 5.4 `behaviors/trigger_roll.py` — TriggerRollBehavior

**Responsibilities:**
- Momentary mode: hold Trigger Roll pad → show quantize submenu (replaces clip-length row)
- Quantize options: 1/4 (1.0 beat), 1/8 (0.5 beat), 1/16 (0.25 beat) — default 1/16
- While Trigger Roll pad + target drum pad held: inject repeated MIDI notes at selected subdivision
- Implementation: use `_Framework.Task.repeat` to schedule `send_midi(note_on)` at interval

```python
class TriggerRollBehavior(BaseBehavior):
    QUANTIZE_OPTIONS = {
        "1/4":  1.0,
        "1/8":  0.5,
        "1/16": 0.25,
    }
    DEFAULT_QUANTIZE = "1/16"

    def _start_roll(self, note: int, velocity: int = 100): ...
    def _stop_roll(self): ...
    def _show_quantize_menu(self): ...
    def _hide_quantize_menu(self): ...
```

> **Implementation note**: Ableton's Arpeggiator workaround is fragile. Use `_Framework.Task`:  
> `self._roll_task = self._task_group.add(Task.repeat(Task.run(self._fire_note)))` with `self._roll_task.set_interval(self._quantize_beats)`.

### 5.5 `behaviors/mute_mode.py` — MuteModeBehavior

**Two sub-modes (toggled via Mute Mode Change pad):**

| Sub-mode | Pad style | Behavior |
|---|---|---|
| **Momentary** (default) | Normal | Hold Mute pad + press drum pad → mute/unmute on release |
| **Latch** | Orange pulse | Mute pad alone enters latch; tap pads to toggle; hold Mute + multi-select → mute all on release |

```python
class MuteModeBehavior(BaseBehavior):
    MODE_MOMENTARY = "momentary"
    MODE_LATCH     = "latch"

    def __init__(self, adapter, song):
        super().__init__(adapter, song)
        self.mode = self.MODE_MOMENTARY
        self._pending_mutes: set[int] = set()  # pads selected during latch hold

    def toggle_mode(self): ...
    def _apply_mutes(self): ...
    def _refresh_pad_states(self): ...
```

LED rules (latch mode):
- Armed, unmuted → slow fade pulse
- Armed, muted → grey (no pulse)
- Empty → off

### 5.6 `behaviors/lock_mode.py` — LockModeBehavior

Three states cycled via toggle press:

```
UNLOCKED → LOCK_TRACK → FULL_LOCK → UNLOCKED
```

| State | Navigation | Behavior |
|---|---|---|
| UNLOCKED | All arrows active | Default; follows session view |
| LOCK_TRACK | Left/Right greyed | Locks to selected track; clip changes still trigger sequencer update |
| FULL_LOCK | All arrows greyed | Locks to track + clip; auto-switches sequencer on clip trigger |

```python
class LockModeBehavior(BaseBehavior):
    STATES = ["unlocked", "lock_track", "full_lock"]

    def cycle(self): ...
    def _update_nav_leds(self): ...
    def _on_clip_triggered(self, clip): ...  # auto-switch in full_lock
```

LED encoding:
- UNLOCKED: dim violet
- LOCK_TRACK: bright violet
- FULL_LOCK: slow violet fade (pulse)

### 5.7 `behaviors/router.py` — BehaviorRouter

```python
class BehaviorRouter:
    """
    Dispatches incoming MIDI messages to the correct behavior.
    Manages behavior lifecycle (enter/exit).
    Handles multi-behavior concurrent state (e.g. TriggerRoll overlaid on StepSequencer).
    """

    def __init__(self, adapter, song):
        self.adapter = adapter
        self.song = song
        self._stack: list[BaseBehavior] = []   # active behavior stack

    def push(self, behavior: BaseBehavior): ...   # enter new mode
    def pop(self): ...                            # exit top mode
    def dispatch(self, msg: MidiMessage): ...     # walk stack top→bottom
    def tick(self): ...                           # forward to all registered behaviors
```

---

## 6. Layer 3 — Material

### 6.1 `material/zone.py`

```python
from dataclasses import dataclass, field

@dataclass
class Zone:
    name: str
    role: str                     # e.g. "drum_selector", "step_grid", "clip_navigation"
    pads: list[int]               # ordered list of pad note numbers
    width: int                    # columns
    height: int                   # rows

    def pad_at(self, row: int, col: int) -> int: ...
    def index_of(self, pad: int) -> tuple[int, int]: ...   # → (row, col)
    def contains(self, pad: int) -> bool: ...
```

### 6.2 `material/base_adapter.py`

```python
from abc import ABC, abstractmethod
from .zone import Zone

class DeviceAdapter(ABC):
    @abstractmethod
    def zone(self, name: str) -> Zone: ...

    @abstractmethod
    def set_pad_rgb(self, pad: int, r: int, g: int, b: int): ...

    @abstractmethod
    def set_pad_palette(self, pad: int, color_index: int): ...

    @abstractmethod
    def set_pad_pulse(self, pad: int, color_index: int): ...

    @abstractmethod
    def set_pad_flash(self, pad: int, color_a: int, color_b: int): ...

    @abstractmethod
    def clear_pad(self, pad: int): ...

    @abstractmethod
    def clear_all(self): ...

    @abstractmethod
    def enter_programmer_mode(self): ...

    @abstractmethod
    def exit_programmer_mode(self): ...
```

### 6.3 `material/launchpad_x.py` — LaunchpadXAdapter

Loads `configs/devices/launchpad_x.json` (converted from YAML) at init. Builds Zone objects from config. Delegates all LED commands to `protocol/sysex.py`.

```python
class LaunchpadXAdapter(DeviceAdapter):
    def __init__(self, send_midi_fn, config_path: str):
        self._send = send_midi_fn
        self._config = self._load_config(config_path)
        self._zones: dict[str, Zone] = self._build_zones()

    def _load_config(self, path: str) -> dict: ...    # json.load
    def _build_zones(self) -> dict[str, Zone]: ...    # config → Zone objects
    def zone(self, name: str) -> Zone: ...
```

### 6.4 `material/color.py` — ColorMapper

Ableton returns chain colors as integers from its internal 70-color palette. Map these to the closest Novation 128-color palette index.

```python
# Ableton color palette (RGB tuples, 70 entries) — embed as constant
ABLETON_COLORS: list[tuple[int,int,int]] = [ ... ]

# Novation Launchpad X palette (RGB tuples, 128 entries) — embed as constant
NOVATION_COLORS: list[tuple[int,int,int]] = [ ... ]

def ableton_to_novation(ableton_index: int) -> int:
    """Nearest-neighbor match in RGB space."""
    rgb = ABLETON_COLORS[ableton_index]
    return _nearest_novation(rgb)

def _nearest_novation(rgb: tuple[int,int,int]) -> int:
    """Euclidean distance in RGB space → closest Novation palette index."""
    ...
```

---

## 7. Configuration Files

### 7.1 `configs/devices/launchpad_x.yaml`

```yaml
device:
  name: Launchpad X
  manufacturer: Novation
  sysex_header: [0x00, 0x20, 0x29, 0x02, 0x0C]
  grid:
    width: 9
    height: 9
    pad_offset: 11       # bottom-left pad MIDI note number
    row_stride: 10       # note increment per row

  zones:
    drum_pad:
      role: drum_selector
      rows: [0, 3]       # inclusive, from bottom
      cols: [0, 3]

    step_sequencer:
      role: step_grid
      rows: [4, 7]
      cols: [0, 7]

    clip_length:
      role: clip_navigation
      rows: [8, 8]
      cols: [0, 7]

    controls:
      role: control_strip
      rows: [0, 7]
      cols: [8, 8]

  cc_map:
    octave_up:   { channel: 1, number: 89 }
    octave_down: { channel: 1, number: 79 }
    nav_up:      { channel: 1, number: 91 }
    nav_down:    { channel: 1, number: 92 }
    nav_left:    { channel: 1, number: 93 }
    nav_right:   { channel: 1, number: 94 }

  palette: novation_128

  special_pads:
    mute_button:       { note: 89 }
    trigger_roll:      { note: 79 }
    lock_toggle:       { note: 19 }
    color_change:      { note: 9  }
```

### 7.2 `configs/behaviors/drum_sequencer.yaml`

```yaml
behavior: DrumSequencer

defaults:
  step_length: "1/16"
  octave_root: "C1"         # MIDI note 36
  lock_state: unlocked

bindings:
  drum_pad:
    zone: drum_pad
    on_press: select_chain
    on_playhead: flash_red
    feedback:
      armed: chain_color
      muted: grey
      empty: off

  step_grid:
    zone: step_sequencer
    on_press_empty: insert_note
    on_press_filled: delete_note
    playhead:
      color: orange
      style: solid
    feedback:
      velocity_to_brightness: true
      muted_style: grey
      muted_playing_style: pulse_red

  clip_nav:
    zone: clip_length
    on_press: scroll_to_beat
    feedback:
      has_content: dim_white
      in_view: bright_white

  trigger_roll:
    pad: trigger_roll
    mode: momentary
    quantize_zone: clip_length    # reuses the row as menu while held
    default_quantize: "1/16"

  mute:
    pad: mute_button
    default_mode: momentary
    latch_color: orange_pulse

  lock:
    pad: lock_toggle
    states:
      unlocked:   { color: violet_dim }
      lock_track: { color: violet_bright }
      full_lock:  { color: violet_pulse }
```

---

## 8. Entry Point

### `__init__.py`

```python
from .LPX95Custom import LPX95Custom

def create_instance(c_instance):
    return LPX95Custom(c_instance)
```

### `LPX95Custom.py`

```python
import Live
from _Framework.ControlSurface import ControlSurface
from material.launchpad_x import LaunchpadXAdapter
from behaviors.router import BehaviorRouter
from behaviors.drum_pad import DrumPadBehavior
from behaviors.step_sequencer import StepSequencerBehavior
from behaviors.trigger_roll import TriggerRollBehavior
from behaviors.mute_mode import MuteModeBehavior
from behaviors.lock_mode import LockModeBehavior
import os, json

class LPX95Custom(ControlSurface):
    def __init__(self, c_instance):
        super().__init__(c_instance)
        with self.component_guard():
            self._setup()

    def _setup(self):
        script_dir = os.path.dirname(os.path.realpath(
            __import__('inspect').getfile(lambda: 0)
        ))
        config_path = os.path.join(script_dir, "configs", "devices", "launchpad_x.json")

        self._adapter = LaunchpadXAdapter(self._send_midi, config_path)
        self._adapter.enter_programmer_mode()

        song = self.song()
        seq  = StepSequencerBehavior(self._adapter, song)
        drum = DrumPadBehavior(self._adapter, song, seq)
        roll = TriggerRollBehavior(self._adapter, song)
        mute = MuteModeBehavior(self._adapter, song)
        lock = LockModeBehavior(self._adapter, song)

        self._router = BehaviorRouter(self._adapter, song)
        self._router.push(lock)
        self._router.push(mute)
        self._router.push(drum)
        self._router.push(seq)   # top of stack; gets first dispatch

    def receive_midi_chunk(self, midi_bytes):
        from protocol.midi import parse
        for status, d1, d2 in midi_bytes:
            self._router.dispatch(parse(status, d1, d2))

    def disconnect(self):
        self._adapter.clear_all()
        self._adapter.exit_programmer_mode()
        super().disconnect()
```

---

## 9. State Bridge — Ableton → WebSocket

### 9.1 Architecture

Ableton's Remote Script sandbox forbids spawning external processes. The bridge works around this via a **shared state file**:

```
LPX95Custom.py
  → writes state.json on every significant change
      ↓
bridge/server.ts  (Node.js, separate terminal / autostart)
  → fs.watch on state.json
  → broadcasts JSON diff over WebSocket (ws://localhost:9001)
      ↓
Control Room browser tab
  → useSequencerState hook subscribes
  → re-renders affected components
```

No polling: state writes are event-driven (on MIDI receive, on playhead tick, on mode change).

### 9.2 State File Schema

The Remote Script writes `state.json` to a well-known path (e.g. `~/.lpx95/state.json`). Schema:

```json
{
  "version": 1,
  "ts": 1234567890.123,
  "bpm": 128.0,
  "is_playing": true,
  "playhead_beat": 3.25,
  "lock_state": "lock_track",
  "active_mode": "step_sequencer",
  "drum_pads": [
    { "index": 0, "note": 36, "color_rgb": [255, 80, 0], "muted": false, "playing": true },
    ...
  ],
  "step_grid": {
    "clip_length_beats": 8.0,
    "scroll_offset_steps": 0,
    "steps": [
      { "col": 0, "row": 0, "active": true, "velocity": 100, "muted": false },
      ...
    ]
  }
}
```

The Remote Script writes this file atomically (write to `.state.tmp`, then `os.rename`). The bridge reads it on each `change` event from `fs.watch`.

### 9.3 Bridge Server (`bridge/server.ts`)

- Node.js + `ws` package + `chokidar` for reliable cross-platform file watching
- On file change: read + parse JSON, diff against last broadcast, send full payload to all connected clients
- WebSocket port: `9001` (configurable via env `BRIDGE_PORT`)
- No auth — local-only, stage network is trusted
- Graceful reconnect: clients must handle connection drops and auto-reconnect

### 9.4 State Writer in Remote Script

Add a `StateWriter` helper (inside `lpx_95_custom/`) that any behavior calls after mutating state:

```python
class StateWriter:
    """Serializes current sequencer state to a JSON file for the bridge."""

    def __init__(self, path: str):
        self._path = path
        self._tmp  = path + ".tmp"

    def write(self, state: dict):
        import json, os
        data = json.dumps(state)
        with open(self._tmp, "w") as f:
            f.write(data)
        os.rename(self._tmp, self._path)   # atomic on POSIX
```

`StateWriter` is instantiated in `LPX95Custom._setup()` and passed to `BehaviorRouter`. The router calls `state_writer.write(router.snapshot())` after every `dispatch()` and every `tick()`. `BehaviorRouter.snapshot()` assembles the full state dict from all active behaviors.

---

## 10. Control Room Frontend

### 10.1 Stack & Constraints

| Concern | Choice | Reason |
|---|---|---|
| Build tool | Vite | Fast HMR for dev; zero-config static build for stage |
| Framework | React 18 | Hooks-first; minimal runtime |
| Styling | Tailwind CSS + DaisyUI | Utility-first; DaisyUI provides light/dark theme tokens out of the box |
| Theme | `data-theme` attribute | DaisyUI built-in; defaults to `dark`; toggleable with a single button |
| Language | TypeScript | Schema types shared with bridge |
| WebSocket | native browser `WebSocket` | No extra dep; wrapped in a custom hook |

No router, no state management library, no form library — the UI is a single-page read-only view.

### 10.2 Theme

DaisyUI theme applied at `<html data-theme="dark">`. A single toggle button (`StatusBar`) switches between `dark` and `light`. Both themes must remain legible in a dark stage environment; the `light` variant is a high-contrast white-on-black alternative, not a pastel day theme.

Tailwind config extends DaisyUI with two custom themes:

```ts
// tailwind.config.ts
daisyui: {
  themes: [
    {
      dark: {
        "primary":         "#f97316",   // amber — playhead, active pads
        "base-100":        "#0a0a0a",   // near-black background
        "base-content":    "#e5e5e5",
        "neutral":         "#1a1a1a",
        "neutral-content": "#737373",
      },
      light: {
        "primary":         "#ea580c",
        "base-100":        "#ffffff",
        "base-content":    "#0a0a0a",
        "neutral":         "#f5f5f5",
        "neutral-content": "#525252",
      },
    },
  ],
}
```

### 10.3 Layout

Single full-screen view, no scrolling. Proportions are fixed to look right on a laptop placed on a DJ booth:

```
┌──────────────────────────────────────────────┐
│  StatusBar  (BPM · lock · mode · conn · ☀/☾) │  h: 3rem
├───────────────────────┬──────────────────────┤
│                       │                      │
│     StepGrid          │     DrumPads         │  flex-1
│     (8×8)             │     (4×4)            │
│                       │                      │
├───────────────────────┴──────────────────────┤
│  Playhead  (beat position bar + clip length)  │  h: 2.5rem
└──────────────────────────────────────────────┘
```

All sizing is `rem`-based; no fixed pixel widths. Works at 1280×800 and above.

### 10.4 Components

#### `useSequencerState.ts`
- Opens `WebSocket` to `ws://localhost:9001`
- On `message`: `JSON.parse` → update state via `useState`
- On `close` / `error`: exponential back-off reconnect (max 8 s)
- Returns `{ state: SequencerState | null, connected: boolean }`

#### `StepGrid.tsx`
- Renders an 8×8 grid of `<div>` cells
- Cell appearance driven by `steps[col][row]`:
  - **Active** → `bg-primary` opacity scaled by `velocity / 127`
  - **Muted** → `bg-neutral-content` dim
  - **Playhead column** → thin amber left border overlay (does not change cell color)
- No click handlers

#### `DrumPads.tsx`
- 4×4 grid; each cell shows chain `color_rgb` as background tint
- Badges: `M` (muted, grey), `▶` (currently playing, amber pulse via DaisyUI `animate-pulse`)
- No click handlers

#### `StatusBar.tsx`
- Left: connection dot (green `●` / red `●`), BPM (large monospace)
- Center: active mode label (`STEP SEQ` / `DRUM PAD` etc.)
- Right: lock state badge (`UNLOCKED` / `LOCK TRACK` / `FULL LOCK`), theme toggle button

#### `Playhead.tsx`
- Single horizontal bar
- A thin vertical line moves left-to-right showing `playhead_beat / clip_length_beats`
- Beat markers below as thin tick marks
- Scroll window indicator (lighter shade) shows which 8-step window is visible in StepGrid

### 10.5 Design Rules (on-stage minimalism)

1. **No text inside grid cells** — state communicated by color and opacity only
2. **No hover states on pads** — hover is meaningless on stage; use `pointer-events-none`
3. **No modals, dropdowns, tooltips** — if it requires interaction, it does not belong here
4. **Font**: monospace only (system `ui-monospace`) — consistent metrics, no FOUT
5. **Transitions**: max 150 ms ease-out on color changes; no entrance/exit animations
6. **Connection loss**: overlay a full-screen semi-transparent `DISCONNECTED` banner — never silently show stale state

---

## 11. Developer Scripts

### 11.1 `scripts/convert_configs.py`

Converts all `configs/**/*.yaml` → `configs/**/*.json`. Run once before installing.

```bash
python scripts/convert_configs.py
```

Requires PyYAML (`pip install pyyaml`) on the developer machine — not needed in Ableton runtime.

### 11.2 `scripts/install.py`

```bash
python scripts/install.py --ableton-path "/Applications/Ableton Live 12.app"
```

Copies `lpx_95_custom/` to `{ableton}/Contents/App-Resources/MIDI Remote Scripts/lpx_95_custom/`. Validates that JSON configs exist (aborts if not converted).

---

## 12. Testing Strategy

Tests run **outside Ableton** using mocks for `Live.*` and `_Framework.*`.

```
tests/
├── mocks/
│   ├── live_mock.py          # Stub Live.Song, Live.Clip, Live.DrumChain
│   └── framework_mock.py     # Stub ControlSurface, Task
├── test_sysex.py             # Encode/decode roundtrips, byte correctness
├── test_zone.py              # pad_at(), index_of(), contains()
├── test_color_mapper.py      # Ableton→Novation nearest-neighbor, edge cases
├── test_step_sequencer.py    # Note insert/delete, scroll, playhead position
└── test_mute_mode.py         # Momentary/latch FSM transitions
```

Run with: `python -m pytest tests/`

---

## 13. Implementation Order

Build in this sequence to maintain testability at each step:

**Python / Ableton layers (steps 1–13):**

1. **`protocol/`** — constants, sysex encoders, MidiMessage. Full unit tests.
2. **`material/zone.py`** — Zone dataclass + geometry helpers. Unit tests.
3. **`material/color.py`** — ColorMapper with hardcoded palettes. Unit tests.
4. **`configs/devices/launchpad_x.yaml`** + convert script → JSON.
5. **`material/launchpad_x.py`** — config loader, zone builder, LED dispatch.
6. **`behaviors/base.py`** + **`router.py`** — skeleton only.
7. **`behaviors/drum_pad.py`** — pad→chain mapping, LED refresh.
8. **`behaviors/step_sequencer.py`** — grid render, note I/O, playhead.
9. **`behaviors/mute_mode.py`** — momentary first, latch second.
10. **`behaviors/lock_mode.py`** — state cycle + nav LED guard.
11. **`behaviors/trigger_roll.py`** — Task-based note scheduler.
12. **`LPX95Custom.py`** + **`__init__.py`** — wire everything, install, smoke test in Ableton.
13. **`configs/behaviors/drum_sequencer.yaml`** — externalize all magic values from step 7–11.

**Bridge + Frontend (steps 14–17, can begin in parallel with step 8+):**

14. **`StateWriter`** + `BehaviorRouter.snapshot()` — define state schema, wire writer into router, verify `state.json` is written correctly on each tick.
15. **`bridge/server.ts`** — Node.js WebSocket server; verify round-trip from file write to WS message in under 50 ms.
16. **`control_room/` scaffold** — Vite + React + Tailwind + DaisyUI; `useSequencerState` hook with mock JSON; verify reconnect logic.
17. **Components** — `StatusBar` first (uses scalar state), then `DrumPads`, then `StepGrid`, then `Playhead`. Wire to live bridge once step 15 is stable.

---

## 14. Key Ableton API Reference

```python
# Song
song = self.song()
song.current_song_time                    # float, beats
song.add_current_song_time_listener(fn)

# Tracks & Devices
track = song.tracks[i]
device = track.devices[0]                 # should be InstrumentRack or DrumRack
chains = device.chains                    # list of DrumChain

# DrumChain
chain.name
chain.color                               # int, Ableton color index
chain.mute                                # bool
chain.solo                               # bool

# Clips
clip_slot = track.clip_slots[i]
clip = clip_slot.clip                     # may be None
clip.get_notes(from_time, from_pitch, time_span, pitch_span)  # → tuple of Note
clip.set_notes(notes_tuple)
clip.remove_notes(from_time, from_pitch, time_span, pitch_span)
clip.loop_end                             # float, beats
clip.is_playing                           # bool

# Note tuple format: (pitch, time, duration, velocity, mute_bool)
```

---

## 15. Known Risks & Mitigations

| Risk | Mitigation |
|---|---|
| SysEx framing inconsistency | Always test with a MIDI monitor (e.g. MIDI Monitor on macOS) before trusting LED output |
| Playhead jitter at high BPM | Throttle `current_song_time` listener: only redraw if step index changed |
| Color mapping accuracy | Embed both full palettes as constants; use perceptual weighting (2r, 4g, 3b) in distance calc |
| TriggerRoll timing drift | Use `song.current_song_time` as clock source, not wall clock; quantize fire time to nearest subdivision |
| Ableton Python version mismatch | Test against Live 11 (Python 3.6) and Live 12 (Python 3.9+); avoid f-strings with `=` specifier |
| YAML not available at runtime | All YAML must be pre-converted to JSON. The install script enforces this. |
| `os.rename` not atomic on Windows | Stage machines are macOS; POSIX rename guarantee holds. Document this assumption. |
| File-write overhead on tick | `StateWriter.write()` only on meaningful state diffs; skip if snapshot hash unchanged. |
| WebSocket disconnection on stage | `useSequencerState` must show `DISCONNECTED` banner immediately — never silently display stale state. |
| Pad color mismatch (Ableton→Novation→RGB) | The `color_rgb` field in state.json uses the already-mapped Novation RGB, not the raw Ableton index — no second mapping needed in the UI. |

---

*End of specification. All sections are self-contained. Claude Code should work top-to-bottom through Section 11 (Implementation Order) and refer back to Sections 4–8 for per-module contracts.*