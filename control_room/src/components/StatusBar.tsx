import type { SequencerState, LockState } from "../types/state";

type View = "room" | "simulator";

interface Props {
  state:          SequencerState | null;
  connected:      boolean;
  theme:          "dark" | "light";
  view:           View;
  onToggleTheme:  () => void;
  onToggleView:   () => void;
  onOpenSettings: () => void;
}

const LOCK_LABELS: Record<LockState, string> = {
  unlocked:   "UNLOCKED",
  lock_track: "LOCK TRACK",
  full_lock:  "FULL LOCK",
};

const LOCK_BADGE_CLASS: Record<LockState, string> = {
  unlocked:   "badge badge-ghost border-neutral-content text-neutral-content",
  lock_track: "badge badge-secondary",
  full_lock:  "badge badge-secondary animate-pulse",
};

const MODE_LABELS: Record<string, string> = {
  step_sequencer: "STEP SEQ",
  drum_pad:       "DRUM PAD",
  trigger_roll:   "ROLL",
  mute:           "MUTE",
};

export function StatusBar({
  state, connected, theme, view,
  onToggleTheme, onToggleView, onOpenSettings,
}: Props) {
  const bpm       = state?.bpm.toFixed(1) ?? "---.-";
  const lockState = state?.lock_state ?? "unlocked";
  const mode      = state?.active_mode ?? "step_sequencer";

  return (
    <div className="flex items-center justify-between px-4 h-12 bg-base-200 border-b border-base-300 shrink-0 font-mono">
      {/* Left: connection + BPM */}
      <div className="flex items-center gap-3">
        <span
          className={`text-xs ${connected ? "text-success" : "text-error"}`}
          title={connected ? "Bridge connected" : "Bridge disconnected"}
        >
          ●
        </span>
        <span className="text-2xl font-bold text-base-content tracking-tight">
          {bpm}
        </span>
        <span className="text-xs text-neutral-content uppercase">BPM</span>
        {state?.is_playing && (
          <span className="text-xs text-primary animate-pulse">▶</span>
        )}
      </div>

      {/* Center: active mode */}
      <span className="text-sm font-bold text-base-content tracking-widest uppercase">
        {view === "simulator"
          ? "SIMULATOR"
          : (MODE_LABELS[mode] ?? mode.toUpperCase())}
      </span>

      {/* Right: lock state + view toggle + theme + settings */}
      <div className="flex items-center gap-2">
        {view === "room" && (
          <span className={LOCK_BADGE_CLASS[lockState]}>
            {LOCK_LABELS[lockState]}
          </span>
        )}

        {/* Simulator toggle */}
        <button
          onClick={onToggleView}
          className={`btn btn-ghost btn-xs font-mono ${view === "simulator" ? "btn-active" : ""}`}
          title={view === "simulator" ? "Back to Control Room" : "Open Simulator"}
        >
          {view === "simulator" ? "⬛" : "⬜"}
        </button>

        {/* Theme toggle */}
        <button
          onClick={onToggleTheme}
          className="btn btn-ghost btn-xs font-mono"
          title="Toggle theme"
        >
          {theme === "dark" ? "☀" : "☾"}
        </button>

        {/* Settings */}
        <button
          onClick={onOpenSettings}
          className="btn btn-ghost btn-xs font-mono"
          title="Settings"
        >
          ⚙
        </button>
      </div>
    </div>
  );
}
