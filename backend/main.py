from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import HumanMessage
from pydantic import BaseModel

from config import settings
from kapruka_mcp.kapruka_tools import get_mcp_stats, kapruka_list_delivery_cities, reset_mcp_stats, resolve_delivery_city
from graph.graph import build_graph
from live.connection_pool import create_session, get_or_create_session, update_agent_state
from ws_stream.stream_handler import handle_stream

_graph = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not settings.kapruka_mcp_url:
        raise RuntimeError("KAPRUKA_MCP_URL is required in backend/.env")
    yield


app = FastAPI(title="Kapruka Agent Backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


@app.get("/health")
def health() -> dict[str, str | bool]:
    return {"status": "ok", "gemini_configured": bool(settings.gemini_api_key)}


@app.get("/dev/mcp-stats")
def dev_mcp_stats() -> dict[str, Any]:
    """Inspect Kapruka MCP call counts — useful to verify rate limits vs timeouts."""
    return get_mcp_stats()


@app.post("/dev/mcp-stats/reset")
@app.get("/dev/mcp-stats/reset")
def dev_mcp_stats_reset() -> dict[str, str]:
    reset_mcp_stats()
    return {"status": "ok", "message": "MCP call counters cleared"}


@app.get("/dev/delivery-cities")
def dev_delivery_cities(query: str | None = None) -> dict[str, Any]:
    """Debug kapruka_list_delivery_cities + canonical resolution."""
    listed = kapruka_list_delivery_cities(query=query, limit=10)
    resolved: str | None = None
    resolve_error: str | None = None
    if query and query.strip():
        try:
            resolved = resolve_delivery_city(query)
        except Exception as exc:
            resolve_error = str(exc)
    return {
        "query": query,
        "listed": listed,
        "resolved": resolved,
        "resolve_error": resolve_error,
    }


class DevInvokeRequest(BaseModel):
    intent: str
    session_id: str | None = None


@app.post("/dev/invoke")
async def dev_invoke(body: DevInvokeRequest) -> dict[str, Any]:
    session = get_or_create_session(body.session_id) if body.session_id else create_session()
    prior_messages = list(session["agent_state"].get("messages") or [])
    initial_state = {
        **session["agent_state"],
        "messages": prior_messages + [HumanMessage(content=body.intent)],
        "next_node": "discovery",
    }

    result = await get_graph().ainvoke(
        initial_state,
        config={"configurable": {"thread_id": session["langgraph_thread_id"]}},
    )
    update_agent_state(session["session_id"], result)

    return {
        "session_id": session["session_id"],
        "ui_action": result.get("ui_action"),
        "cart": result.get("cart"),
        "delivery_info": result.get("delivery_info"),
        "voice_prompt": result.get("voice_prompt"),
    }


@app.websocket("/ws/stream/{session_id}")
async def ws_stream(websocket: WebSocket, session_id: str) -> None:
    await handle_stream(websocket, session_id)
