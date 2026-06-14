"""Phase 3 five-step pause/resume handoff (Model 1 -> LangGraph -> Model 1 -> UI)."""

from __future__ import annotations

import json
import logging
from contextlib import suppress
from typing import Any

from fastapi import WebSocket

from kapruka_mcp.kapruka_tools import get_mcp_stats
from live.connection_pool import get_session
from live.gemini_client import GeminiLiveSession
from live.text_intent import emit_assistant_text, emit_ui_result, invoke_graph_intent

logger = logging.getLogger(__name__)

HANDOFF_TIMEOUT_SECONDS = 35.0


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

    with suppress(Exception):
        await websocket.send_json(
            {"type": "text", "role": "user", "content": intent_text}
        )

    try:
        await websocket.send_json({"type": "control", "action": "processing"})
    except Exception:
        pass
    logger.info("Handoff started for session %s: %s", session_id, intent_text)

    voice_prompt = "Done."
    result: dict[str, Any] | None = None

    try:
        # Step 3 — Run LangGraph (Model 2)
        result, voice_prompt, prior_agent_state = await invoke_graph_intent(
            session_id=session_id,
            intent_text=intent_text,
            voice_mode=True,
            pool_session=pool_session,
        )

        # Step 4 — Return tool response to Model 1 (voice before UI)
        await live_session.send_tool_response(
            call_id=call_id,
            name=call_name,
            result=voice_prompt,
        )
        logger.info("Sent tool response to Model 1 for session %s", session_id)

        # Sync voice reply into chat transcript
        await emit_assistant_text(websocket, voice_prompt)

        # Step 5 — Emit UI event to client
        if result:
            await emit_ui_result(websocket, result, prior_agent_state=prior_agent_state)
            ui_action = result.get("ui_action") or {}
            if ui_action.get("action") == "show_checkout":
                logger.info(
                    "Emitted checkout link for session %s: %s",
                    session_id,
                    (ui_action.get("payload") or {}).get("checkout_url"),
                )
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
            await emit_assistant_text(websocket, voice_prompt)
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
