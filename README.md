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

## Run FastAPI (dev)

```bash
cd backend
uvicorn main:app --reload
```
