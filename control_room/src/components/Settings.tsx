import { useState, useEffect } from "react";
import type { Preferences } from "../../bridge/schema";

const BRIDGE = "http://localhost:9001";

interface Props {
  onClose: () => void;
}

interface MidiDevice {
  id: string;
  name: string;
}

export function Settings({ onClose }: Props) {
  const [inputs,  setInputs]  = useState<MidiDevice[]>([]);
  const [outputs, setOutputs] = useState<MidiDevice[]>([]);
  const [prefs,   setPrefs]   = useState<Preferences>({});
  const [saved,   setSaved]   = useState(false);
  const [midiErr, setMidiErr] = useState<string | null>(null);

  // Load saved preferences + enumerate MIDI devices
  useEffect(() => {
    fetch(`${BRIDGE}/preferences`)
      .then((r) => r.json())
      .then((p: Preferences) => setPrefs(p))
      .catch(() => {});

    if (!navigator.requestMIDIAccess) {
      setMidiErr("Web MIDI API not available in this browser.");
      return;
    }

    navigator
      .requestMIDIAccess({ sysex: false })
      .then((midi) => {
        const ins:  MidiDevice[] = [];
        const outs: MidiDevice[] = [];
        midi.inputs.forEach((dev)  => ins.push({ id: dev.id,  name: dev.name ?? dev.id }));
        midi.outputs.forEach((dev) => outs.push({ id: dev.id, name: dev.name ?? dev.id }));
        setInputs(ins);
        setOutputs(outs);

        // Re-enumerate when devices change
        midi.onstatechange = () => {
          const i2: MidiDevice[] = [];
          const o2: MidiDevice[] = [];
          midi.inputs.forEach((dev)  => i2.push({ id: dev.id,  name: dev.name ?? dev.id }));
          midi.outputs.forEach((dev) => o2.push({ id: dev.id,  name: dev.name ?? dev.id }));
          setInputs(i2);
          setOutputs(o2);
        };
      })
      .catch((err: unknown) => setMidiErr(String(err)));
  }, []);

  function save() {
    fetch(`${BRIDGE}/preferences`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify(prefs),
    })
      .then(() => {
        setSaved(true);
        setTimeout(() => setSaved(false), 2000);
      })
      .catch(() => {});
  }

  function update(patch: Partial<Preferences>) {
    setPrefs((p) => ({ ...p, ...patch }));
  }

  return (
    /* Modal backdrop */
    <div
      className="fixed inset-0 bg-base-100/70 flex items-center justify-center z-50"
      onClick={onClose}
    >
      <div
        className="bg-base-200 border border-base-300 rounded-lg p-6 w-96 font-mono text-sm"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <span className="font-bold tracking-widest uppercase text-base-content">
            Settings
          </span>
          <button className="btn btn-ghost btn-xs" onClick={onClose}>✕</button>
        </div>

        {/* MIDI section */}
        <div className="mb-4">
          <p className="text-[10px] uppercase tracking-widest text-neutral-content mb-2">
            MIDI Devices
          </p>

          {midiErr ? (
            <p className="text-error text-xs">{midiErr}</p>
          ) : (
            <>
              <label className="block mb-2">
                <span className="text-[10px] text-neutral-content uppercase">Input</span>
                <select
                  className="select select-bordered select-sm w-full mt-1 font-mono"
                  value={prefs.midi_input ?? ""}
                  onChange={(e) => update({ midi_input: e.target.value })}
                >
                  <option value="">— none —</option>
                  {inputs.map((d) => (
                    <option key={d.id} value={d.name}>{d.name}</option>
                  ))}
                </select>
              </label>

              <label className="block mb-2">
                <span className="text-[10px] text-neutral-content uppercase">Output</span>
                <select
                  className="select select-bordered select-sm w-full mt-1 font-mono"
                  value={prefs.midi_output ?? ""}
                  onChange={(e) => update({ midi_output: e.target.value })}
                >
                  <option value="">— none —</option>
                  {outputs.map((d) => (
                    <option key={d.id} value={d.name}>{d.name}</option>
                  ))}
                </select>
              </label>

              {inputs.length === 0 && outputs.length === 0 && (
                <p className="text-neutral-content text-xs">
                  No MIDI devices found. Connect your Launchpad X and refresh.
                </p>
              )}
            </>
          )}
        </div>

        {/* Port overrides */}
        <div className="mb-4">
          <p className="text-[10px] uppercase tracking-widest text-neutral-content mb-2">
            Ports
          </p>
          <div className="flex gap-2">
            <label className="flex-1">
              <span className="text-[10px] text-neutral-content uppercase">Bridge</span>
              <input
                type="number"
                className="input input-bordered input-sm w-full mt-1 font-mono"
                value={prefs.bridge_port ?? 9001}
                onChange={(e) => update({ bridge_port: parseInt(e.target.value, 10) })}
              />
            </label>
            <label className="flex-1">
              <span className="text-[10px] text-neutral-content uppercase">Simulator</span>
              <input
                type="number"
                className="input input-bordered input-sm w-full mt-1 font-mono"
                value={prefs.simulator_port ?? 9002}
                onChange={(e) => update({ simulator_port: parseInt(e.target.value, 10) })}
              />
            </label>
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center justify-between mt-4">
          <span className={`text-xs transition-opacity ${saved ? "text-success opacity-100" : "opacity-0"}`}>
            Saved to ~/.lpx95/preferences.json
          </span>
          <button className="btn btn-primary btn-sm" onClick={save}>
            Save
          </button>
        </div>
      </div>
    </div>
  );
}
