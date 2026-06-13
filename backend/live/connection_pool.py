from __future__ import annotations

import asyncio
import uuid
from typing import Any

from graph.state import AgentState


sessions: dict[str, dict[str, Any]] = {}


def create_session(session_id: str | None = None) -> dict[str, Any]:
    sid = session_id or str(uuid.uuid4())
    session = {
        "live_session": None,
        "langgraph_thread_id": str(uuid.uuid4()),
        "agent_state": _empty_agent_state(),
        "websocket": None,
        "audio_frozen": False,
        "handoff_running": False,
        "graph_lock": asyncio.Lock(),
    }
    sessions[sid] = session
    session["session_id"] = sid
    return session


def get_or_create_session(session_id: str) -> dict[str, Any]:
    if session_id in sessions:
        session = sessions[session_id]
        session.setdefault("graph_lock", asyncio.Lock())
        session.setdefault("handoff_running", False)
        return session
    return create_session(session_id)


def get_session(session_id: str) -> dict[str, Any]:
    if session_id not in sessions:
        raise KeyError(f"Unknown session: {session_id}")
    return sessions[session_id]


def update_agent_state(session_id: str, state: AgentState) -> None:
    get_session(session_id)["agent_state"] = state


def _empty_agent_state() -> AgentState:
    return {
        "messages": [],
        "cart": [],
        "delivery_info": {},
        "checkout_info": {},
        "ui_action": {},
        "voice_prompt": "",
        "next_node": "discovery",
    }
