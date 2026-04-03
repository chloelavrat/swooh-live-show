import { useState, useEffect, useRef } from "react";
import type { SequencerState } from "../types/state";

const WS_URL       = "ws://localhost:9001";
const INITIAL_BACKOFF = 500;   // ms
const MAX_BACKOFF     = 8000;  // ms

interface UseSequencerStateResult {
  state:     SequencerState | null;
  connected: boolean;
}

export function useSequencerState(): UseSequencerStateResult {
  const [state,     setState]     = useState<SequencerState | null>(null);
  const [connected, setConnected] = useState(false);

  const wsRef      = useRef<WebSocket | null>(null);
  const backoffRef = useRef(INITIAL_BACKOFF);
  const timerRef   = useRef<ReturnType<typeof setTimeout> | null>(null);
  const unmounted  = useRef(false);

  function connect() {
    if (unmounted.current) return;

    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      if (unmounted.current) return;
      setConnected(true);
      backoffRef.current = INITIAL_BACKOFF;   // reset on successful connect
    };

    ws.onmessage = (event: MessageEvent<string>) => {
      if (unmounted.current) return;
      try {
        const parsed = JSON.parse(event.data) as SequencerState;
        setState(parsed);
      } catch {
        // Malformed JSON — ignore
      }
    };

    ws.onclose = () => {
      if (unmounted.current) return;
      setConnected(false);

      // Exponential back-off reconnect
      timerRef.current = setTimeout(() => {
        backoffRef.current = Math.min(backoffRef.current * 2, MAX_BACKOFF);
        connect();
      }, backoffRef.current);
    };

    ws.onerror = () => {
      // onclose fires after onerror — reconnect handled there
      ws.close();
    };
  }

  useEffect(() => {
    unmounted.current = false;
    connect();

    return () => {
      unmounted.current = true;
      if (timerRef.current) clearTimeout(timerRef.current);
      wsRef.current?.close();
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return { state, connected };
}
