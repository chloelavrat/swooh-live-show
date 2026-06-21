# LPX95 Custom — Novation Launchpad X for Ableton Live

A custom MIDI Remote Script for the Novation Launchpad X, built for live performance. Includes a React control room UI and a hardware simulator for development without physical gear.

---

## Architecture

```
lpx_95_custom/     Python — Ableton Remote Script + behavior stack
control_room/      TypeScript/React — browser-based control room UI
  bridge/          Node.js WebSocket + HTTP bridge (port 9001)
```

State flows one way: Ableton → `state.json` (atomic write) → bridge (file watcher) → WebSocket → UI.

---

## Pad Layout (Programmer Mode)

```
[ ↑  ↓  ←  →  ·  ·  ·  · ] [ nav ]
[ clip length navigation   ] [ nav ]   ← clip nav / quantize submenu
[ step sequencer  (4 × 8)  ] [ ctrl]
[ step sequencer           ]
[ step sequencer           ]
[ step sequencer           ]
[ drum pads (4 × 4) · · ·  ] [ ctrl]   MUTE ROLL MCHG · · · · LOCK
```

---

## Behaviors

### Drum Pad (4×4, bottom-left)
- Each pad maps to a Drum Rack chain. Colors match Ableton chain colors.
- Pressing a pad selects that chain and switches the step sequencer to its pitch.
- Octave shift: right strip pads **↑** (CC 89) / **↓** (CC 79).
- **Red flash** when a note fires at the playhead.
- **Grey** = muted. **Off** = empty.
- **Color change mode**: hold pad 9 (logo) + press a drum pad → pick from 16-color palette.

### Step Sequencer (4×8, upper-left)
- Shows notes for the selected drum chain at 1/16 resolution.
- **Amber column** = current playhead position.
- **Green** = active note (brightness = velocity). **Grey** = muted.
- Muted notes **pulse red** when the playhead hits them.
- If the playhead is outside the visible window, the nav row **flashes red** at the current beat.
- Press a step to toggle a note (velocity 100).
- **Clip nav row** (top row): shows clip length (1 pad = 1 beat). Press to scroll the view.

### Lock Mode (pad 19)
Toggle cycles: **Unlocked** → **Lock Track** → **Full Lock** → Unlocked

| State | Lock pad | Nav arrows |
|---|---|---|
| Unlocked | Dim violet | All white |
| Lock Track | Bright violet | ←→ greyed |
| Full Lock | Violet pulse | All greyed |

In Full Lock, the step sequencer auto-switches when a new clip starts playing.

### Trigger Roll (pad 79, momentary)
Hold Roll pad + hold a drum pad → fires the note repeatedly.  
Quantize submenu appears in the clip nav row: **1/4 · 1/8 · 1/16** (default 1/16).

### Mute Mode (pad 89)
**Momentary** (default): hold Mute + press drum pads → immediate toggle.

**Latch** (enter/exit via pad 69 `MCHG`):
- Tap a drum pad directly → immediate mute/unmute.
- Hold Mute + tap pads → they pulse green (staged) → release Mute → all applied.
- Mute pad pulses amber. Armed pads pulse green.

---

## Run

```bash
# Setup (first time)
make setup

# With real Launchpad X + Ableton
make run

# Without hardware (simulator)
make run-simulator

# Python simulator only
make simulator

# Install Ableton script
make install
```

`make run-simulator` starts three processes: bridge (port 9001), Python simulator (port 9002), and the React dev server.

### Running on real hardware (Launchpad X + Ableton)

The simulator fakes both the Launchpad and Ableton — it writes `state.json` itself.
With a real Launchpad X, Ableton's Remote Script writes that file instead, so the
flow is different:

1. **Stop the simulator** if it's running (`make run-simulator`) — it competes with
   the real script over `~/.lpx95/state.json`.

2. **Install the Remote Script into Ableton:**
   ```bash
   make install
   ```
   This copies `lpx_95_custom/` into Ableton's `MIDI Remote Scripts` directory.
   It auto-detects Ableton Live 11/12. For a non-standard location:
   ```bash
   make convert
   python lpx_95_custom/scripts/install.py --ableton-path "/path/to/Ableton Live 12 Suite.app"
   ```

3. **Configure Ableton** — Preferences → Link/Tempo/MIDI → MIDI:
   - **Control Surface** → `lpx_95_custom`
   - **Input** and **Output** → your **Launchpad X** ports
   - Restart Ableton if the script doesn't appear in the list.

4. **Start bridge + UI** (no simulator):
   ```bash
   make run
   ```
   State now flows: Ableton → Remote Script → `state.json` → bridge → UI.

> Verify the Launchpad is connected in **Audio MIDI Setup → MIDI Studio** (macOS)
> before launching — it should appear as "Launchpad X".

---

## Development

```bash
# Run tests
make test

# Convert YAML configs to JSON
make convert
```

Tests live in `lpx_95_custom/tests/`. The mock framework (`tests/mocks/`) stubs out `Live` and `_Framework` so behaviors can be tested outside Ableton.

---

## Preferences

Saved to `~/.lpx95/preferences.json` via `POST http://localhost:9001/preferences`.  
Set bridge/simulator ports and MIDI device in the Settings panel (⚙ in the UI).
