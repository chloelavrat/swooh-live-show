import { useState, useEffect } from "react";
import { useSequencerState } from "./hooks/useSequencerState";
import { StatusBar }  from "./components/StatusBar";
import { StepGrid }   from "./components/StepGrid";
import { DrumPads }   from "./components/DrumPads";
import { Playhead }   from "./components/Playhead";
import { Simulator }  from "./components/Simulator";
import { Settings }   from "./components/Settings";
import type { Preferences } from "../bridge/schema";

type Theme = "dark" | "light";
type View  = "room" | "simulator";

const BRIDGE = "http://localhost:9001";

export default function App() {
  const { state, connected } = useSequencerState();

  const [theme,        setTheme]        = useState<Theme>("dark");
  const [view,         setView]         = useState<View>("room");
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [prefs,        setPrefs]        = useState<Preferences>({});

  // Apply theme to <html>
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);

  // Load preferences on mount (theme + port config)
  useEffect(() => {
    fetch(`${BRIDGE}/preferences`)
      .then((r) => r.json())
      .then((p: Preferences) => {
        setPrefs(p);
        if (p.theme) setTheme(p.theme);
      })
      .catch(() => {});
  }, []);

  function toggleTheme() {
    const next: Theme = theme === "dark" ? "light" : "dark";
    setTheme(next);
    // Persist theme change immediately
    fetch(`${BRIDGE}/preferences`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ ...prefs, theme: next }),
    }).catch(() => {});
  }

  const simulatorPort = prefs.simulator_port ?? 9002;

  return (
    <div className="flex flex-col h-screen w-screen overflow-hidden bg-base-100 select-none">
      <StatusBar
        state={state}
        connected={connected}
        theme={theme}
        view={view}
        onToggleTheme={toggleTheme}
        onToggleView={() => setView((v) => (v === "room" ? "simulator" : "room"))}
        onOpenSettings={() => setSettingsOpen(true)}
      />

      {view === "room" ? (
        <>
          <div className="flex flex-1 overflow-hidden">
            <StepGrid state={state} />
            <div className="w-px bg-base-300 shrink-0" />
            <DrumPads state={state} />
          </div>
          <Playhead state={state} />
        </>
      ) : (
        <Simulator state={state} simulatorPort={simulatorPort} />
      )}

      {settingsOpen && <Settings onClose={() => setSettingsOpen(false)} />}

      {/* Disconnected overlay — never silently show stale state */}
      {!connected && (
        <div className="absolute inset-0 bg-base-100/80 flex items-center justify-center pointer-events-none">
          <span className="text-error font-mono font-bold text-xl tracking-widest animate-pulse">
            DISCONNECTED
          </span>
        </div>
      )}
    </div>
  );
}
