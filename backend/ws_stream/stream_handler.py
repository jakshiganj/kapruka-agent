"""Multiplexed WebSocket stream: PCM in, audio + UI JSON out."""

from __future__ import annotations

import asyncio
import base64
import json
import logging
from contextlib import suppress
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

from config import settings
from live.connection_pool import get_or_create_session, update_agent_state
from live.gemini_client import GeminiLiveSession
from live.handoff import run_intent_handoff
from graph.category_catalog import catalog_label
from live.text_intent import TextIntentBusyError, emit_assistant_text, run_text_intent

logger = logging.getLogger(__name__)


async def _emit_transcription(
    websocket: WebSocket,
    *,
    role: str,
    content: str,
    final: bool,
) -> None:
    if not content:
        return
    with suppress(Exception):
        await websocket.send_json(
            {
                "type": "transcript",
                "role": role,
                "content": content,
                "final": final,
            }
        )


async def _forward_transcriptions(
    websocket: WebSocket,
    message: Any,
) -> None:
    server_content = getattr(message, "server_content", None)
    if not server_content:
        return

    input_tx = getattr(server_content, "input_transcription", None)
    if input_tx and getattr(input_tx, "text", None):
        await _emit_transcription(
            websocket,
            role="user",
            content=input_tx.text,
            final=bool(getattr(input_tx, "finished", False)),
        )

    output_tx = getattr(server_content, "output_transcription", None)
    if output_tx and getattr(output_tx, "text", None):
        await _emit_transcription(
            websocket,
            role="assistant",
            content=output_tx.text,
            final=bool(getattr(output_tx, "finished", False)),
        )


async def _forward_live_to_client(
    *,
    session_id: str,
    live_session: GeminiLiveSession,
    websocket: WebSocket,
    pool_session: dict,
) -> None:
    handoff_lock = asyncio.Lock()

    async def _run_handoff(tool_call: Any) -> None:
        if pool_session.get("handoff_running"):
            function_calls = tool_call.function_calls or []
            if function_calls and function_calls[0].id:
                fc = function_calls[0]
                logger.warning(
                    "Duplicate Kapruka handoff ignored for session %s (already running)",
                    session_id,
                )
                await live_session.send_tool_response(
                    call_id=fc.id,
                    name=fc.name or "send_intent_to_backend",
                    result="I'm already searching Kapruka — please hold on a moment.",
                )
            return

        pool_session["handoff_running"] = True
        try:
            async with handoff_lock:
                await run_intent_handoff(
                    session_id=session_id,
                    live_session=live_session,
                    websocket=websocket,
                    tool_call=tool_call,
                    pool_session=pool_session,
                )
        except Exception:
            logger.exception("Unhandled handoff error for session %s", session_id)
        finally:
            pool_session["handoff_running"] = False

    try:
        async for message in live_session.receive_messages():
            await _forward_transcriptions(websocket, message)

            if message.tool_call:
                asyncio.create_task(
                    _run_handoff(message.tool_call),
                    name=f"handoff-{session_id}",
                )
                continue

            if message.data:
                await websocket.send_json(
                    {
                        "type": "audio",
                        "data": base64.b64encode(message.data).decode("ascii"),
                    }
                )
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception("Live forward loop failed for session %s", session_id)
        raise
    else:
        if not live_session.is_connected:
            with suppress(Exception):
                await websocket.send_json(
                    {
                        "type": "control",
                        "action": "live_error",
                        "message": (
                            "Voice connection to Gemini dropped. "
                            "Toggle the mic off and on to reconnect."
                        ),
                    }
                )


async def _start_live_session(
    *,
    session_id: str,
    websocket: WebSocket,
    pool_session: dict,
) -> tuple[GeminiLiveSession | None, asyncio.Task | None, asyncio.Task | None]:
    """Lazily connect Gemini Live and start the forward loop."""

    existing = pool_session.get("live_session")
    if existing and existing.is_connected:
        with suppress(Exception):
            await websocket.send_json({"type": "control", "action": "live_ready"})
        return existing, pool_session.get("forward_task"), pool_session.get("watch_task")

    if not settings.gemini_api_key:
        with suppress(Exception):
            await websocket.send_json(
                {
                    "type": "control",
                    "action": "live_error",
                    "message": "Voice requires GEMINI_API_KEY in backend/.env.",
                }
            )
        return None, None, None

    live_session = GeminiLiveSession()
    pool_session["live_session"] = live_session

    try:
        await live_session.connect()
    except Exception as exc:
        logger.exception("Failed to connect Gemini Live session for %s", session_id)
        pool_session["live_session"] = None
        user_message = (
            str(exc)
            if "GEMINI_API_KEY" in str(exc) or "timed out" in str(exc).lower()
            else (
                "Voice service unavailable. Check GEMINI_API_KEY in backend/.env "
                "and your network connection, then try enabling the mic again."
            )
        )
        with suppress(Exception):
            await websocket.send_json(
                {
                    "type": "control",
                    "action": "live_error",
                    "message": user_message,
                }
            )
        return None, None, None

    forward_task = asyncio.create_task(
        _forward_live_to_client(
            session_id=session_id,
            live_session=live_session,
            websocket=websocket,
            pool_session=pool_session,
        )
    )

    async def _watch_forward() -> None:
        try:
            await forward_task
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.exception("Forward task crashed for session %s", session_id)

    watch_task = asyncio.create_task(_watch_forward())
    pool_session["forward_task"] = forward_task
    pool_session["watch_task"] = watch_task

    with suppress(Exception):
        await websocket.send_json({"type": "control", "action": "live_ready"})
    return live_session, forward_task, watch_task


async def _stop_live_session(pool_session: dict) -> None:
    forward_task = pool_session.pop("forward_task", None)
    watch_task = pool_session.pop("watch_task", None)
    live_session: GeminiLiveSession | None = pool_session.get("live_session")

    if forward_task:
        forward_task.cancel()
        with suppress(asyncio.CancelledError):
            await forward_task
    if watch_task:
        watch_task.cancel()
        with suppress(asyncio.CancelledError):
            await watch_task
    if live_session:
        await live_session.close()
    pool_session["live_session"] = None
    pool_session["audio_frozen"] = False


async def _handle_select_category(
    *,
    session_id: str,
    websocket: WebSocket,
    pool_session: dict,
    category: str,
    subcategory: str | None = None,
    label: str | None = None,
) -> None:
    category = (category or "").strip()
    if not category:
        return

    if pool_session.get("handoff_running"):
        logger.info("Category tap ignored during handoff for session %s", session_id)
        return

    display_label = (label or "").strip() or catalog_label(category)
    if subcategory:
        display_label = subcategory

    agent_state = dict(pool_session.get("agent_state") or {})
    payload: dict[str, Any] = {
        "category": category,
        "search_query": subcategory or display_label,
        "category_label": display_label,
    }
    if subcategory:
        payload["subcategory"] = subcategory

    agent_state["ui_action"] = {
        "action": "show_products",
        "payload": payload,
    }
    update_agent_state(session_id, agent_state)

    intent = f"Browse {display_label}"
    try:
        await run_text_intent(
            session_id=session_id,
            websocket=websocket,
            intent_text=intent,
            voice_mode=True,
            pool_session=pool_session,
        )
        logger.info(
            "Category browse for session %s: %s / %s",
            session_id,
            category,
            subcategory or display_label,
        )
    except TextIntentBusyError:
        await emit_assistant_text(
            websocket,
            "Still working on your last request — please wait a moment.",
        )
    except Exception:
        logger.exception("Failed category browse for session %s", session_id)
        with suppress(Exception):
            await websocket.send_json(
                {
                    "type": "control",
                    "action": "error",
                    "message": (
                        "Could not load that category right now. "
                        "Please try again or tell Kapru what you'd like to send."
                    ),
                }
            )


async def _handle_select_product(
    *,
    session_id: str,
    websocket: WebSocket,
    pool_session: dict,
    product_id: str,
) -> None:
    agent_state = dict(pool_session.get("agent_state") or {})
    ui_action = dict(agent_state.get("ui_action") or {})
    payload = dict(ui_action.get("payload") or {})
    products = payload.get("products") or []
    selected = next((p for p in products if p.get("id") == product_id), None)
    if not selected:
        return

    if pool_session.get("handoff_running"):
        logger.info("Product tap ignored during handoff for session %s", session_id)
        return

    payload["selected_product"] = selected
    ui_action["payload"] = payload
    agent_state["ui_action"] = ui_action
    update_agent_state(session_id, agent_state)

    intent = f"Add {selected.get('name', 'this item')} to cart"
    try:
        await run_text_intent(
            session_id=session_id,
            websocket=websocket,
            intent_text=intent,
            voice_mode=True,
            pool_session=pool_session,
        )
        logger.info(
            "Added selected product to cart for session %s: %s",
            session_id,
            selected.get("name"),
        )
    except TextIntentBusyError:
        await emit_assistant_text(
            websocket,
            "Still working on your last request — please wait a moment.",
        )
    except Exception:
        logger.exception("Failed to add selected product for session %s", session_id)
        with suppress(Exception):
            await websocket.send_json(
                {
                    "type": "control",
                    "action": "error",
                    "message": (
                        "Could not add that item right now. "
                        "Please try tapping again or tell Kapru the product name."
                    ),
                }
            )


async def handle_stream(websocket: WebSocket, session_id: str) -> None:
    await websocket.accept()

    pool_session = get_or_create_session(session_id)
    pool_session["websocket"] = websocket
    pool_session["audio_frozen"] = False
    pool_session["live_session"] = None
    pool_session["forward_task"] = None
    pool_session["watch_task"] = None

    with suppress(Exception):
        await websocket.send_json({"type": "control", "action": "session_ready"})

    try:
        while True:
            message = await websocket.receive()
            if message.get("type") == "websocket.disconnect":
                break

            text = message.get("text")
            if text:
                try:
                    ctrl = json.loads(text)
                except json.JSONDecodeError:
                    continue

                ctrl_type = ctrl.get("type")

                if ctrl_type == "text_message":
                    user_text = (ctrl.get("text") or "").strip()
                    if not user_text:
                        continue
                    if pool_session.get("handoff_running"):
                        await emit_assistant_text(
                            websocket,
                            "Still working on your last request — please wait a moment.",
                        )
                        continue
                    try:
                        await run_text_intent(
                            session_id=session_id,
                            websocket=websocket,
                            intent_text=user_text,
                            voice_mode=False,
                            pool_session=pool_session,
                        )
                    except TextIntentBusyError:
                        await emit_assistant_text(
                            websocket,
                            "Still working on your last request — please wait a moment.",
                        )
                    continue

                if ctrl_type == "voice_start":
                    await _start_live_session(
                        session_id=session_id,
                        websocket=websocket,
                        pool_session=pool_session,
                    )
                    continue

                if ctrl_type == "voice_stop":
                    await _stop_live_session(pool_session)
                    with suppress(Exception):
                        await websocket.send_json({"type": "control", "action": "session_ready"})
                    continue

                if ctrl_type == "select_product":
                    product_id = ctrl.get("product_id")
                    if product_id:
                        await _handle_select_product(
                            session_id=session_id,
                            websocket=websocket,
                            pool_session=pool_session,
                            product_id=product_id,
                        )
                    continue

                if ctrl_type == "select_category":
                    category = ctrl.get("category")
                    if category:
                        await _handle_select_category(
                            session_id=session_id,
                            websocket=websocket,
                            pool_session=pool_session,
                            category=str(category),
                            subcategory=ctrl.get("subcategory"),
                            label=ctrl.get("label"),
                        )
                    continue

            pcm_chunk = message.get("bytes")
            if pcm_chunk is None:
                continue

            live_session: GeminiLiveSession | None = pool_session.get("live_session")
            if not live_session or not live_session.is_connected:
                continue

            if pool_session.get("audio_frozen"):
                continue

            await live_session.send_pcm_audio(pcm_chunk)
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected: %s", session_id)
    finally:
        await _stop_live_session(pool_session)
        pool_session["websocket"] = None
