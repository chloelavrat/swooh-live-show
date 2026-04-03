import type { DrumPad, SequencerState } from "../types/state";

interface Props {
  state: SequencerState | null;
}

const GRID = 4;  // 4×4

function rgbToCss([r, g, b]: [number, number, number]): string {
  return `rgb(${r},${g},${b})`;
}

function isDark([r, g, b]: [number, number, number]): boolean {
  // Simple luminance check for badge contrast
  return 0.299 * r + 0.587 * g + 0.114 * b < 128;
}

interface PadCellProps {
  pad: DrumPad | null;
}

function PadCell({ pad }: PadCellProps) {
  if (!pad) {
    return (
      <div
        className="rounded bg-base-300 pointer-events-none"
        aria-hidden="true"
      />
    );
  }

  const color     = pad.color_rgb;
  const hasColor  = color[0] + color[1] + color[2] > 10;
  const bg        = hasColor ? rgbToCss(color) : undefined;
  const textClass = hasColor && isDark(color) ? "text-white" : "text-black";

  return (
    <div
      className={`relative rounded pointer-events-none flex items-start justify-start p-1`}
      style={{
        backgroundColor: bg ?? "var(--b3)",
        opacity: pad.muted ? 0.35 : 1,
        transition: "opacity 100ms ease-out, background-color 100ms ease-out",
      }}
      aria-hidden="true"
    >
      {/* Muted badge */}
      {pad.muted && (
        <span className={`text-[7px] font-mono font-bold leading-none ${textClass} opacity-80`}>
          M
        </span>
      )}
      {/* Playing indicator */}
      {pad.playing && !pad.muted && (
        <span className={`text-[7px] font-mono font-bold leading-none animate-pulse ${textClass}`}>
          ▶
        </span>
      )}
    </div>
  );
}

export function DrumPads({ state }: Props) {
  const pads = state?.drum_pads ?? [];

  return (
    <div className="flex flex-col gap-[3px] p-3 w-40 shrink-0">
      <span className="text-[9px] text-neutral-content font-mono uppercase tracking-widest mb-1">
        Drum Pads
      </span>
      <div
        className="grid gap-[3px] flex-1"
        style={{
          gridTemplateColumns: `repeat(${GRID}, 1fr)`,
          gridTemplateRows:    `repeat(${GRID}, 1fr)`,
        }}
      >
        {Array.from({ length: GRID * GRID }, (_, i) => (
          <PadCell key={i} pad={pads[i] ?? null} />
        ))}
      </div>
    </div>
  );
}
