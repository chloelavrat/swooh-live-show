import type { SequencerState } from "../types/state";

interface Props {
  state: SequencerState | null;
}

const GRID_COLS = 8;
const GRID_ROWS = 4;  // hardware zone is 4 rows × 8 cols

function velocityOpacity(velocity: number): number {
  // Map 1–127 → 0.3–1.0
  return 0.3 + (velocity / 127) * 0.7;
}

export function StepGrid({ state }: Props) {
  const steps    = state?.step_grid.steps ?? [];
  const scrollOffset = state?.step_grid.scroll_offset_steps ?? 0;
  const playheadBeat = state?.playhead_beat ?? 0;
  const stepLength   = 0.25;  // 1/16 in beats
  const playheadStep = Math.floor(playheadBeat / stepLength) % (GRID_COLS * GRID_ROWS);
  const playheadCol  = playheadStep % GRID_COLS;

  // Build a fast lookup: "row-col" → step
  const stepMap = new Map<string, typeof steps[0]>();
  for (const step of steps) {
    stepMap.set(`${step.row}-${step.col}`, step);
  }

  return (
    <div className="flex flex-col gap-[3px] p-3 flex-1">
      <span className="text-[9px] text-neutral-content font-mono uppercase tracking-widest mb-1">
        Step Grid — offset {scrollOffset}
      </span>
      <div
        className="grid gap-[3px] flex-1"
        style={{
          gridTemplateColumns: `repeat(${GRID_COLS}, 1fr)`,
          gridTemplateRows:    `repeat(${GRID_ROWS}, 1fr)`,
        }}
      >
        {Array.from({ length: GRID_ROWS }, (_, row) =>
          Array.from({ length: GRID_COLS }, (_, col) => {
            const step = stepMap.get(`${row}-${col}`);
            const isPlayhead = col === playheadCol;
            const isActive   = step?.active ?? false;
            const isMuted    = step?.muted  ?? false;
            const velocity   = step?.velocity ?? 0;

            let bg = "bg-base-300";
            let opacity = 1;
            let extraClass = "";

            if (isActive && !isMuted) {
              bg      = "bg-primary";
              opacity = velocityOpacity(velocity);
            } else if (isActive && isMuted) {
              bg = "bg-neutral-content";
              opacity = 0.35;
            }

            if (isPlayhead) {
              extraClass = "ring-1 ring-inset ring-primary";
            }

            return (
              <div
                key={`${row}-${col}`}
                className={`rounded-sm ${bg} ${extraClass} pointer-events-none`}
                style={{ opacity, transition: "background-color 100ms ease-out, opacity 100ms ease-out" }}
                aria-hidden="true"
              />
            );
          })
        )}
      </div>
    </div>
  );
}
