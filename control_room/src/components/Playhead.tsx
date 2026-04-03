import type { SequencerState } from "../types/state";

interface Props {
  state: SequencerState | null;
}

export function Playhead({ state }: Props) {
  const playheadBeat  = state?.playhead_beat ?? 0;
  const clipLength    = state?.step_grid.clip_length_beats ?? 0;
  const scrollOffset  = (state?.step_grid.scroll_offset_steps ?? 0) * 0.25;  // steps → beats
  const viewLength    = 8 * 0.25;   // 8 cols × 1/16 = 2 beats

  const progress      = clipLength > 0 ? Math.min(playheadBeat / clipLength, 1) : 0;
  const viewStart     = clipLength > 0 ? scrollOffset / clipLength : 0;
  const viewEnd       = clipLength > 0 ? Math.min((scrollOffset + viewLength) / clipLength, 1) : 0;

  // Beat ticks
  const totalBeats    = Math.ceil(clipLength);
  const beatTicks     = clipLength > 0
    ? Array.from({ length: totalBeats }, (_, i) => ({
        pos: i / clipLength,
        label: i % 4 === 0 ? String(i + 1) : null,
      }))
    : [];

  return (
    <div className="flex flex-col gap-1 px-4 py-2 h-10 bg-base-200 border-t border-base-300 shrink-0 font-mono">
      {/* Track */}
      <div className="relative h-3 bg-base-300 rounded overflow-hidden">
        {/* Scroll window */}
        <div
          className="absolute top-0 h-full bg-base-content opacity-10 pointer-events-none"
          style={{
            left:  `${viewStart * 100}%`,
            width: `${(viewEnd - viewStart) * 100}%`,
            transition: "left 80ms ease-out, width 80ms ease-out",
          }}
        />
        {/* Beat ticks */}
        {beatTicks.map(({ pos }) => (
          <div
            key={pos}
            className="absolute top-0 h-full w-px bg-base-content opacity-20 pointer-events-none"
            style={{ left: `${pos * 100}%` }}
          />
        ))}
        {/* Playhead needle */}
        {clipLength > 0 && (
          <div
            className="absolute top-0 h-full w-0.5 bg-primary pointer-events-none"
            style={{
              left:       `${progress * 100}%`,
              transition: "left 60ms linear",
            }}
          />
        )}
      </div>

      {/* Beat labels */}
      <div className="relative h-2">
        {beatTicks
          .filter(({ label }) => label !== null)
          .map(({ pos, label }) => (
            <span
              key={pos}
              className="absolute text-[7px] text-neutral-content pointer-events-none"
              style={{ left: `${pos * 100}%`, transform: "translateX(-50%)" }}
            >
              {label}
            </span>
          ))}
      </div>
    </div>
  );
}
