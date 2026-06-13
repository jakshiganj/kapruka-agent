# Kapruka AI Shopping Agent

Backend agent for the Kapruka Agent Challenge 2026.

## Setup

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
cp .env.example .env     # then fill in GEMINI_API_KEY
```

Note: MCP wrappers live in `backend/kapruka_mcp/` (renamed from `mcp/` to avoid shadowing the official `mcp` Python package).

## Phase 1 — MCP smoke test

```bash
cd backend
python test_mcp.py
```

## Phase 2 — LangGraph end-to-end test

Requires `GEMINI_API_KEY` in `.env` only if router falls back to the LLM; the default test intent uses deterministic routing.

```bash
cd backend
python test_graph.py
```

## Phase 3 — Gemini Live + WebSocket

WebSocket route: `ws://127.0.0.1:8000/ws/stream/{session_id}`

- **Client → server:** raw binary PCM (16 kHz, 16-bit, little-endian)
- **Server → client:** JSON envelopes `{ "type": "audio", "data": "<base64>" }` or `{ "type": "ui", "action": "...", "payload": {...} }`

When Model 1 calls `send_intent_to_backend`, the server runs the 5-step handoff: freeze mic → LangGraph → tool response (voice) → UI event.

```bash
cd backend
uvicorn main:app --reload
python test_handoff.py   # simulates tool call without microphone
```

Note: WebSocket handlers live in `backend/ws_stream/` (not `websockets/`) to avoid shadowing the PyPI `websockets` package required by google-genai.

## Phase 4 — Frontend (React + Vite)

```bash
# Terminal 1 — backend
cd backend
uvicorn main:app --reload

# Terminal 2 — frontend
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173), click **Start Voice Session**, allow microphone access, and speak (e.g. *"I want to send a chocolate cake to Kadawatha on 2026-06-25"*).

The Vite dev server proxies `/ws`, `/health`, and `/dev` to the backend on port 8000.
