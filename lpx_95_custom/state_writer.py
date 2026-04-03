"""
StateWriter — serialises sequencer state to a JSON file for the bridge.

Writes atomically via POSIX os.rename (write to .tmp, then rename).
Safe to call on every tick/dispatch; the router skips writes when state hash is unchanged.
"""

import json
import os
import threading


class StateWriter:

    def __init__(self, path: str):
        self._path = path
        self._tmp  = path + ".tmp"
        self._lock = threading.Lock()
        parent = os.path.dirname(path)
        if parent and not os.path.isdir(parent):
            os.makedirs(parent, exist_ok=True)

    def write(self, state: dict):
        data = json.dumps(state, default=str)
        with self._lock:
            with open(self._tmp, "w") as f:
                f.write(data)
            os.rename(self._tmp, self._path)
