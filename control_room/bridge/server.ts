/**
 * LPX95 Bridge Server
 *
 * Single port (9001) serves both:
 *   - WebSocket: broadcasts state.json to connected Control Room clients
 *   - HTTP GET  /preferences  → reads  ~/.lpx95/preferences.json
 *   - HTTP POST /preferences  → writes ~/.lpx95/preferences.json
 *
 * Usage:
 *   npx tsx bridge/server.ts
 *   BRIDGE_PORT=9001 STATE_FILE=/custom/path.json npx tsx bridge/server.ts
 */

import * as fs from "fs";
import * as path from "path";
import * as os from "os";
import * as http from "http";
import { WebSocketServer, WebSocket } from "ws";
import chokidar from "chokidar";
import type { SequencerState, Preferences } from "./schema";

const PORT        = parseInt(process.env.BRIDGE_PORT  ?? "9001", 10);
const STATE_FILE  = process.env.STATE_FILE  ?? path.join(os.homedir(), ".lpx95", "state.json");
const PREFS_FILE  = process.env.PREFS_FILE  ?? path.join(os.homedir(), ".lpx95", "preferences.json");

// -----------------------------------------------------------------------
// State
// -----------------------------------------------------------------------

let lastPayload: string | null = null;
const clients = new Set<WebSocket>();

// -----------------------------------------------------------------------
// HTTP handler (preferences + health)
// -----------------------------------------------------------------------

function cors(res: http.ServerResponse) {
  res.setHeader("Access-Control-Allow-Origin",  "*");
  res.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");
}

function jsonResponse(res: http.ServerResponse, status: number, body: unknown) {
  cors(res);
  res.writeHead(status, { "Content-Type": "application/json" });
  res.end(JSON.stringify(body));
}

function handleHttp(req: http.IncomingMessage, res: http.ServerResponse) {
  cors(res);

  // CORS preflight
  if (req.method === "OPTIONS") {
    res.writeHead(204);
    res.end();
    return;
  }

  // GET /preferences
  if (req.url === "/preferences" && req.method === "GET") {
    try {
      const raw = fs.readFileSync(PREFS_FILE, "utf-8");
      jsonResponse(res, 200, JSON.parse(raw));
    } catch {
      jsonResponse(res, 200, {});
    }
    return;
  }

  // POST /preferences
  if (req.url === "/preferences" && req.method === "POST") {
    let body = "";
    req.on("data", (chunk) => (body += chunk));
    req.on("end", () => {
      try {
        const prefs: Preferences = JSON.parse(body);
        fs.mkdirSync(path.dirname(PREFS_FILE), { recursive: true });
        fs.writeFileSync(PREFS_FILE, JSON.stringify(prefs, null, 2));
        console.log(`[bridge] Preferences saved to ${PREFS_FILE}`);
        jsonResponse(res, 200, { ok: true });
      } catch (err: unknown) {
        jsonResponse(res, 400, { error: String(err) });
      }
    });
    return;
  }

  // GET /health
  if (req.url === "/health" && req.method === "GET") {
    jsonResponse(res, 200, {
      ok:      true,
      clients: clients.size,
      state:   lastPayload !== null,
    });
    return;
  }

  res.writeHead(404);
  res.end();
}

// -----------------------------------------------------------------------
// HTTP + WebSocket server on the same port
// -----------------------------------------------------------------------

const httpServer = http.createServer(handleHttp);
const wss        = new WebSocketServer({ server: httpServer });

wss.on("connection", (ws) => {
  clients.add(ws);
  console.log(`[bridge] Client connected (${clients.size} total)`);

  if (lastPayload !== null) {
    ws.send(lastPayload);
  }

  ws.on("close", () => {
    clients.delete(ws);
    console.log(`[bridge] Client disconnected (${clients.size} remaining)`);
  });

  ws.on("error", (err) => {
    console.error("[bridge] Client error:", err.message);
    clients.delete(ws);
  });
});

httpServer.listen(PORT, () => {
  console.log(`[bridge] Listening on http://localhost:${PORT}  (HTTP + WebSocket)`);
  console.log(`[bridge] Watching state file: ${STATE_FILE}`);
});

// -----------------------------------------------------------------------
// File watcher → broadcast to WS clients
// -----------------------------------------------------------------------

function readAndBroadcast() {
  try {
    const raw = fs.readFileSync(STATE_FILE, "utf-8");
    if (raw === lastPayload) return;
    lastPayload = raw;

    const state: SequencerState = JSON.parse(raw);
    const payload = JSON.stringify(state);

    for (const ws of clients) {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(payload);
      }
    }
  } catch (err: unknown) {
    const msg = String(err);
    if (!msg.includes("ENOENT")) {
      console.error("[bridge] Read error:", msg);
    }
  }
}

fs.mkdirSync(path.dirname(STATE_FILE), { recursive: true });

const watcher = chokidar.watch(STATE_FILE, {
  persistent:       true,
  ignoreInitial:    false,
  usePolling:       false,
  awaitWriteFinish: false,
  disableGlobbing:  true,
});

watcher
  .on("add",    readAndBroadcast)
  .on("change", readAndBroadcast)
  .on("error",  (err) => console.error("[bridge] Watcher error:", err));

// -----------------------------------------------------------------------
// Graceful shutdown
// -----------------------------------------------------------------------

function shutdown() {
  console.log("\n[bridge] Shutting down…");
  watcher.close();
  wss.close();
  httpServer.close(() => process.exit(0));
}

process.on("SIGINT",  shutdown);
process.on("SIGTERM", shutdown);
