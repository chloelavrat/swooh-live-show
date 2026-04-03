/**
 * State schema — shared source of truth between bridge/server.ts and src/types/state.ts.
 * The Python StateWriter serialises this exact structure to state.json.
 */

export interface DrumPad {
  index: number;
  note: number;
  color_rgb: [number, number, number];
  muted: boolean;
  playing: boolean;
}

export interface Step {
  col: number;
  row: number;
  active: boolean;
  velocity: number;
  muted: boolean;
}

export interface StepGrid {
  clip_length_beats: number;
  scroll_offset_steps: number;
  steps: Step[];
}

export type LockState = "unlocked" | "lock_track" | "full_lock";
export type ActiveMode = "step_sequencer" | "drum_pad" | "trigger_roll" | "mute";

export interface SequencerState {
  version: number;
  ts: number;
  bpm: number;
  is_playing: boolean;
  playhead_beat: number;
  lock_state: LockState;
  active_mode: ActiveMode;
  drum_pads: DrumPad[];
  step_grid: StepGrid;
  mute_mode?: string;
  trigger_roll_active?: boolean;
  trigger_roll_quantize?: string;
  /** LED state written by the simulator. Key = pad note number (string). */
  leds?: Record<string, [number, number, number]>;
}

export interface Preferences {
  midi_input?:    string;
  midi_output?:   string;
  bridge_port?:   number;
  simulator_port?: number;
  theme?:         "dark" | "light";
}
