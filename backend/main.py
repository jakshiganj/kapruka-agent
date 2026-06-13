from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from langchain_core.messages import HumanMessage
from pydantic import BaseModel

from config import settings
from graph.graph import build_graph
from live.connection_pool import create_session, update_agent_state

_graph = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not settings.kapruka_mcp_url:
        raise RuntimeError("KAPRUKA_MCP_URL is required in backend/.env")
    yield


app = FastAPI(title="Kapruka Agent Backend", lifespan=lifespan)


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


@app.get("/health")
def health() -> dict[str, str | bool]:
    return {"status": "ok", "gemini_configured": bool(settings.gemini_api_key)}


class DevInvokeRequest(BaseModel):
    intent: str
    session_id: str | None = None


@app.post("/dev/invoke")
async def dev_invoke(body: DevInvokeRequest) -> dict[str, Any]:
    session = create_session(body.session_id)
    initial_state = {
        **session["agent_state"],
        "messages": [HumanMessage(content=body.intent)],
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
