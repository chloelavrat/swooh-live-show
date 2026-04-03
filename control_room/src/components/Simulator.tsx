import { useState } from "react";
import type { SequencerState } from "../types/state";

interface Props {
  state:          SequencerState | null;
  simulatorPort:  number;
}

// ── Pad layout ────────────────────────────────────────────────────────────────
// Launchpad X programmer mode:
//   note = 11 + col + row * 10  (row 0 = bottom, col 0 = left, 9 cols × 9 rows)
//   Col 8 = right control strip: notes 19, 29, 39, 49, 59, 69, 79, 89
//   Row 8 = top strip:            notes 91, 92, 93, 94, 95, 96, 97, 98
//   Special: note 9 (logo/mode button shown separately)

function noteAt(row: number, col: number): number {
  return 11 + col + row * 10;
}

// Zone classification for visual hint when no LED is set
function zoneOf(row: number, col: number): string {
  if (row === 8 && col <= 7) return "clip";
  if (row >= 4 && row <= 7 && col <= 7) return "seq";
  if (row <= 3 && col <= 3) return "drum";
  if (col === 8) return "ctrl";
  return "empty";
}

const ZONE_BASE_CLASS: Record<string, string> = {
  clip:  "bg-base-300 opacity-60",
  seq:   "bg-base-300 opacity-40",
  drum:  "bg-base-300 opacity-80",
  ctrl:  "bg-base-300 opacity-30",
  empty: "bg-base-300 opacity-10",
};

// Special pad labels for the control strip
const CTRL_LABELS: Record<number, string> = {
  89: "MUTE",
  79: "ROLL",
  69: "MCHG",
  59: "",
  49: "",
  39: "",
  29: "",
  19: "LOCK",
};

const TOP_LABELS: Record<number, string> = {
  91: "▲",
  92: "▼",
  93: "◀",
  94: "▶",
};

// ── Pad component ─────────────────────────────────────────────────────────────

interface PadProps {
  note:          number;
  row:           number;
  col:           number;
  leds:          Record<string, [number, number, number]>;
  onNoteOn:      (note: number) => void;
  onNoteOff:     (note: number) => void;
}

function Pad({ note, row, col, leds, onNoteOn, onNoteOff }: PadProps) {
  const [pressed, setPressed] = useState(false);
  const led = leds[String(note)];
  const zone = zoneOf(row, col);

  const hasLed = led !== undefined && (led[0] + led[1] + led[2]) > 5;
  const bg     = hasLed ? `rgb(${led[0]},${led[1]},${led[2]})` : undefined;

  // Label: special pads show their name
  let label = "";
  if (col === 8) label = CTRL_LABELS[note] ?? "";
  else if (row === 8) label = TOP_LABELS[note] ?? "";

  function handleDown(e: React.MouseEvent | React.TouchEvent) {
    e.preventDefault();
    setPressed(true);
    onNoteOn(note);
  }

  function handleUp(e: React.MouseEvent | React.TouchEvent) {
    e.preventDefault();
    if (pressed) {
      setPressed(false);
      onNoteOff(note);
    }
  }

  return (
    <div
      onMouseDown={handleDown}
      onMouseUp={handleUp}
      onMouseLeave={handleUp}
      onTouchStart={handleDown}
      onTouchEnd={handleUp}
      className={`
        relative flex items-center justify-center rounded cursor-pointer select-none
        transition-all duration-75
        ${!hasLed ? ZONE_BASE_CLASS[zone] : ""}
        ${pressed ? "scale-90 brightness-150" : ""}
      `}
      style={{
        backgroundColor: bg,
        boxShadow: hasLed ? `0 0 6px 1px rgba(${led![0]},${led![1]},${led![2]},0.5)` : undefined,
      }}
    >
      {label && (
        <span className="text-[7px] font-mono font-bold text-neutral-content opacity-70 leading-none pointer-events-none">
          {label}
        </span>
      )}
    </div>
  );
}

// ── BPM control ───────────────────────────────────────────────────────────────

function BpmControl({ bpm, simulatorPort }: { bpm: number; simulatorPort: number }) {
  const [value, setValue] = useState(String(Math.round(bpm)));

  function commit() {
    const v = parseInt(value, 10);
    if (isNaN(v) || v < 20 || v > 300) return;
    fetch(`http://localhost:${simulatorPort}/tempo`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ bpm: v }),
    }).catch(() => {});
  }

  return (
    <div className="flex items-center gap-2">
      <span className="text-[10px] text-neutral-content uppercase tracking-widest">BPM</span>
      <input
        type="number"
        min={20} max={300}
        className="input input-bordered input-xs w-16 font-mono text-center"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onBlur={commit}
        onKeyDown={(e) => e.key === "Enter" && commit()}
      />
    </div>
  );
}

// ── Simulator view ────────────────────────────────────────────────────────────

export function Simulator({ state, simulatorPort }: Props) {
  const leds = (state?.leds ?? {}) as Record<string, [number, number, number]>;
  const bpm  = state?.bpm ?? 120;

  function sendMidi(status: number, note: number, velocity: number) {
    fetch(`http://localhost:${simulatorPort}/midi`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ status, data1: note, data2: velocity }),
    }).catch(() => {});
  }

  const noteOn  = (note: number) => sendMidi(0x90, note, 100);
  const noteOff = (note: number) => sendMidi(0x80, note, 0);

  return (
    <div className="flex flex-col flex-1 overflow-hidden p-3 gap-2">
      {/* Header row */}
      <div className="flex items-center justify-between shrink-0">
        <span className="text-[9px] font-mono uppercase tracking-widest text-neutral-content">
          Launchpad X — Programmer Mode
        </span>
        <BpmControl bpm={bpm} simulatorPort={simulatorPort} />
      </div>

      {/* 9×9 grid rendered bottom-to-top (row 0 at bottom) */}
      <div
        className="flex-1"
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(9, 1fr)",
          gridTemplateRows:    "repeat(9, 1fr)",
          gap: "3px",
        }}
      >
        {/* Render rows top-to-bottom visually → row 8 first */}
        {Array.from({ length: 9 }, (_, visualRow) => {
          const row = 8 - visualRow;   // flip: visual row 0 = hardware row 8
          return Array.from({ length: 9 }, (_, col) => {
            const note = noteAt(row, col);
            return (
              <Pad
                key={`${row}-${col}`}
                note={note}
                row={row}
                col={col}
                leds={leds}
                onNoteOn={noteOn}
                onNoteOff={noteOff}
              />
            );
          });
        })}
      </div>

      {/* Zone legend */}
      <div className="flex gap-4 shrink-0">
        {[
          { zone: "drum",  label: "Drum (4×4)" },
          { zone: "seq",   label: "Step Seq (4×8)" },
          { zone: "clip",  label: "Clip Nav" },
          { zone: "ctrl",  label: "Controls" },
        ].map(({ zone, label }) => (
          <div key={zone} className="flex items-center gap-1">
            <div className={`w-2 h-2 rounded-sm ${ZONE_BASE_CLASS[zone]}`} />
            <span className="text-[8px] text-neutral-content font-mono">{label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
