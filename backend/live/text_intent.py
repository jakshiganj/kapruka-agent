"""Shared LangGraph invocation for typed text and tap-to-add intents."""

from __future__ import annotations

import asyncio
import logging
from contextlib import suppress
from typing import Any

from fastapi import WebSocket
from langchain_core.messages import HumanMessage

from graph.graph import build_graph
from graph.ui_envelope import enrich_ui_payload
from kapruka_mcp.kapruka_tools import KaprukaMCPError, get_mcp_stats
from live import session_store
from live.connection_pool import update_agent_state

try:  # LangGraph wraps a cancelled node call in this error on timeout.
    from langgraph.errors import NodeCancelledError
except Exception:  # pragma: no cover - fallback if the symbol moves
    class NodeCancelledError(Exception):
        ...

logger = logging.getLogger(__name__)

HANDOFF_TIMEOUT_SECONDS = 45.0


def _timeout_reply(prior_agent_state: dict[str, Any]) -> tuple[None, str, dict[str, Any]]:
    """Message for a graph timeout — advise waiting when Kapruka is rate-limiting."""
    stats = get_mcp_stats()
    if stats.get("rate_limit_errors", 0) > 0:
        return None, (
            "Kapruka is busy and rate-limiting requests right now. "
            "Your cart is safe — please wait about a minute, then try again."
        ), prior_agent_state
    in_flight = stats.get("in_flight") or []
    if in_flight or stats.get("network_calls", 0) == 0:
        return None, (
            "The request timed out before Kapruka finished responding "
            "(often after a server reload or a slow connection). "
            "Your cart is safe — wait a few seconds and try again."
        ), prior_agent_state
    return None, (
        "The Kapruka search took too long to finish. "
        "This is usually a timeout, not your fault — please try once more in a few seconds."
    ), prior_agent_state


def _is_timeout_cancellation(exc: BaseException) -> bool:
    """True when an exception is a graph cancellation caused by our wait_for timeout."""
    if isinstance(exc, NodeCancelledError):
        return True
    cause = getattr(exc, "__cause__", None)
    return isinstance(cause, asyncio.CancelledError)

_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


class TextIntentBusyError(Exception):
    """Raised when another graph run is already in progress."""


async def invoke_graph_intent(
    *,
    session_id: str,
    intent_text: str,
    voice_mode: bool,
    pool_session: dict[str, Any],
) -> tuple[dict[str, Any] | None, str, dict[str, Any]]:
    """Run LangGraph and persist state. Returns (result, voice_prompt, prior_agent_state)."""

    intent_text = (intent_text or "").strip()
    prior_agent_state = dict(pool_session.get("agent_state") or {})
    if not intent_text:
        return None, "I didn't catch that. Could you repeat what you'd like to order?", prior_agent_state

    agent_state = prior_agent_state
    prior_messages = list(agent_state.get("messages") or [])
    invoke_state = {
        **agent_state,
        "messages": prior_messages + [HumanMessage(content=intent_text)],
        "voice_mode": voice_mode,
    }

    async def _run_graph() -> dict[str, Any]:
        async with pool_session["graph_lock"]:
            return await get_graph().ainvoke(
                invoke_state,
                config={
                    "configurable": {"thread_id": pool_session["langgraph_thread_id"]},
                    "recursion_limit": 12,
                },
            )

    try:
        result = await asyncio.wait_for(_run_graph(), timeout=HANDOFF_TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        stats = get_mcp_stats()
        logger.warning(
            "Graph intent timed out for session %s after %.0fs (MCP network=%s rate_limits=%s in_flight=%s)",
            session_id,
            HANDOFF_TIMEOUT_SECONDS,
            stats["network_calls"],
            stats["rate_limit_errors"],
            stats.get("in_flight"),
        )
        # If Kapruka has been rate-limiting us, retrying immediately only makes it
        # worse — tell the user to pause instead of hammering checkout again.
        return _timeout_reply(prior_agent_state)
    except KaprukaMCPError as exc:
        message = str(exc).removeprefix("Error:").strip()
        if "rate limit" in message.lower():
            return None, (
                "Kapruka's rate limit was hit. "
                "Please wait about a minute before searching again."
            ), prior_agent_state
        return None, f"Kapruka returned an error: {message}", prior_agent_state
    except Exception as exc:
        # On timeout, wait_for cancels the running node; LangGraph re-raises that
        # as NodeCancelledError, which would otherwise look like a hard crash.
        if _is_timeout_cancellation(exc):
            logger.warning(
                "Graph intent cancelled by timeout for session %s (likely slow/rate-limited MCP)",
                session_id,
            )
            return _timeout_reply(prior_agent_state)
        logger.exception("Graph intent failed for session %s", session_id)
        return None, (
            "Sorry, I had trouble reaching Kapruka just now. "
            "Please wait a moment and try again."
        ), prior_agent_state

    update_agent_state(session_id, result)
    await session_store.save_agent_state(session_id, result)
    voice_prompt = result.get("voice_prompt") or "Done."
    return result, voice_prompt, prior_agent_state


async def emit_assistant_text(websocket: WebSocket, content: str) -> None:
    with suppress(Exception):
        await websocket.send_json(
            {"type": "text", "role": "assistant", "content": content}
        )


async def emit_ui_result(
    websocket: WebSocket,
    result: dict[str, Any],
    *,
    prior_agent_state: dict[str, Any] | None = None,
) -> None:
    ui_action = result.get("ui_action") or {}
    action = ui_action.get("action")
    if not action:
        return
    if action == "show_checkout" and prior_agent_state:
        prior_url = (prior_agent_state.get("checkout_result") or {}).get("checkout_url")
        new_url = (result.get("checkout_result") or {}).get("checkout_url")
        if prior_url and new_url and prior_url == new_url:
            return
    await websocket.send_json(
        {
            "type": "ui",
            "action": action,
            "payload": enrich_ui_payload(result),
        }
    )


async def run_text_intent(
    *,
    session_id: str,
    websocket: WebSocket,
    intent_text: str,
    voice_mode: bool,
    pool_session: dict[str, Any],
    emit_user_text: bool = False,
) -> dict[str, Any] | None:
    """Run LangGraph for a user intent and emit text + UI envelopes to the client."""

    intent_text = (intent_text or "").strip()
    if not intent_text:
        return None

    if pool_session.get("handoff_running"):
        raise TextIntentBusyError()

    pool_session["handoff_running"] = True
    try:
        with suppress(Exception):
            await websocket.send_json({"type": "control", "action": "processing"})

        if emit_user_text:
            with suppress(Exception):
                await websocket.send_json(
                    {"type": "text", "role": "user", "content": intent_text}
                )

        result, voice_prompt, prior_agent_state = await invoke_graph_intent(
            session_id=session_id,
            intent_text=intent_text,
            voice_mode=voice_mode,
            pool_session=pool_session,
        )

        await emit_assistant_text(websocket, voice_prompt)

        if result:
            await emit_ui_result(websocket, result, prior_agent_state=prior_agent_state)
            logger.info("Text intent complete for session %s: %s", session_id, intent_text[:80])
            return result

        with suppress(Exception):
            await websocket.send_json(
                {
                    "type": "control",
                    "action": "error",
                    "message": voice_prompt,
                }
            )
        return None
    finally:
        pool_session["handoff_running"] = False
        with suppress(Exception):
            await websocket.send_json({"type": "control", "action": "mic_resume"})
