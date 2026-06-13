"""Phase 3 five-step pause/resume handoff (Model 1 -> LangGraph -> Model 1 -> UI)."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import WebSocket
from langchain_core.messages import HumanMessage

from graph.graph import build_graph
from graph.ui_envelope import enrich_ui_payload
from kapruka_mcp.kapruka_tools import KaprukaMCPError, get_mcp_stats
from live.connection_pool import get_session, update_agent_state
from live.gemini_client import GeminiLiveSession

logger = logging.getLogger(__name__)

HANDOFF_TIMEOUT_SECONDS = 35.0

_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


def _parse_tool_args(raw_args: Any) -> dict[str, Any]:
    if isinstance(raw_args, dict):
        return raw_args
    if isinstance(raw_args, str):
        try:
            parsed = json.loads(raw_args)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            return {"intent_text": raw_args}
    return {}


async def run_intent_handoff(
    *,
    session_id: str,
    live_session: GeminiLiveSession,
    websocket: WebSocket,
    tool_call: Any,
    pool_session: dict[str, Any] | None = None,
) -> None:
    """Execute the 5-step handoff from project.md Section 7."""

    function_calls = tool_call.function_calls or []
    if not function_calls:
        logger.warning("Tool call received with no function_calls")
        return

    function_call = function_calls[0]
    call_id = function_call.id
    call_name = function_call.name or "send_intent_to_backend"

    if function_call.name != "send_intent_to_backend":
        logger.warning("Unexpected tool call: %s", function_call.name)
        if call_id:
            await live_session.send_tool_response(
                call_id=call_id,
                name=call_name,
                result="That action is not supported.",
            )
        return

    args = _parse_tool_args(function_call.args)
    intent_text = (args.get("intent_text") or "").strip()
    if not call_id:
        logger.warning("Tool call missing call_id; cannot resume Model 1")
        return
    if not intent_text:
        await live_session.send_tool_response(
            call_id=call_id,
            name=call_name,
            result="I didn't catch that. Could you repeat what you'd like to order?",
        )
        return

    pool_session = pool_session or get_session(session_id)

    pool_session["audio_frozen"] = True
    await websocket.send_json({"type": "control", "action": "mic_pause"})

    try:
        await websocket.send_json({"type": "control", "action": "processing"})
    except Exception:
        pass
    logger.info("Handoff started for session %s: %s", session_id, intent_text)

    voice_prompt = "Done."
    ui_action: dict[str, Any] = {}

    try:
        # Step 3 — Run LangGraph (Model 2)
        agent_state = dict(pool_session["agent_state"])
        prior_messages = list(agent_state.get("messages") or [])
        invoke_state = {
            **agent_state,
            "messages": prior_messages + [HumanMessage(content=intent_text)],
            "voice_mode": True,
        }

        async def _run_graph() -> dict[str, Any]:
            async with pool_session["graph_lock"]:
                return await get_graph().ainvoke(
                    invoke_state,
                    config={"configurable": {"thread_id": pool_session["langgraph_thread_id"]}},
                )

        result = await asyncio.wait_for(_run_graph(), timeout=HANDOFF_TIMEOUT_SECONDS)
        update_agent_state(session_id, result)

        ui_action = result.get("ui_action") or {}
        voice_prompt = result.get("voice_prompt") or "Done."

        # Step 4 — Return tool response to Model 1 (voice before UI)
        await live_session.send_tool_response(
            call_id=call_id,
            name=call_name,
            result=voice_prompt,
        )
        logger.info("Sent tool response to Model 1 for session %s", session_id)

        # Step 5 — Emit UI event to client
        action = ui_action.get("action")
        if action:
            await websocket.send_json(
                {
                    "type": "ui",
                    "action": action,
                    "payload": enrich_ui_payload(result),
                }
            )
            if action == "show_checkout":
                logger.info(
                    "Emitted checkout link for session %s: %s",
                    session_id,
                    (ui_action.get("payload") or {}).get("checkout_url"),
                )
    except asyncio.CancelledError:
        logger.warning("Handoff cancelled for session %s", session_id)
        voice_prompt = (
            "Kapruka search was interrupted. Please try your search again in a moment."
        )
        try:
            await live_session.send_tool_response(
                call_id=call_id,
                name=call_name,
                result=voice_prompt,
            )
        except Exception:
            logger.exception("Failed to send cancelled tool response")
    except asyncio.TimeoutError:
        stats = get_mcp_stats()
        logger.warning(
            "Handoff timed out for session %s after %.0fs (MCP network calls this session: %s, rate limits: %s)",
            session_id,
            HANDOFF_TIMEOUT_SECONDS,
            stats["network_calls"],
            stats["rate_limit_errors"],
        )
        voice_prompt = (
            "The Kapruka search took too long to finish. "
            "This is usually a timeout, not your fault — please try once more in a few seconds."
        )
        try:
            await live_session.send_tool_response(
                call_id=call_id,
                name=call_name,
                result=voice_prompt,
            )
            logger.info("Sent timeout tool response to Model 1 for session %s", session_id)
        except Exception:
            logger.exception("Failed to send timeout tool response")
    except KaprukaMCPError as exc:
        message = str(exc).removeprefix("Error:").strip()
        is_rate_limit = "rate limit" in message.lower()
        logger.warning(
            "Kapruka MCP error during handoff for session %s (%s): %s",
            session_id,
            "rate limit" if is_rate_limit else "api error",
            message,
        )
        if is_rate_limit:
            voice_prompt = (
                "Kapruka's rate limit was hit. "
                "Please wait about a minute before searching again."
            )
        else:
            voice_prompt = f"Kapruka returned an error: {message}"
        try:
            await live_session.send_tool_response(
                call_id=call_id,
                name=call_name,
                result=voice_prompt,
            )
            logger.info("Sent MCP error tool response to Model 1 for session %s", session_id)
        except Exception:
            logger.exception("Failed to send MCP error tool response")
    except Exception:
        logger.exception("Handoff failed for session %s", session_id)
        voice_prompt = (
            "Sorry, I had trouble reaching Kapruka just now. "
            "Please wait a moment and try again."
        )
        try:
            await live_session.send_tool_response(
                call_id=call_id,
                name=call_name,
                result=voice_prompt,
            )
            logger.info("Sent error tool response to Model 1 for session %s", session_id)
        except Exception:
            logger.exception("Failed to send error tool response")
    finally:
        pool_session["audio_frozen"] = False
        try:
            await websocket.send_json({"type": "control", "action": "mic_resume"})
        except Exception:
            logger.exception("Failed to send mic_resume for session %s", session_id)
        stats = get_mcp_stats()
        logger.info(
            "Handoff complete for session %s (MCP network=%s cache_hits=%s rate_limits=%s)",
            session_id,
            stats["network_calls"],
            stats["cache_hits"],
            stats["rate_limit_errors"],
        )
