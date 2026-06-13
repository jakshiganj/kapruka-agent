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
from live.handoff import get_graph, run_intent_handoff
from graph.ui_envelope import enrich_ui_payload
from langchain_core.messages import HumanMessage

logger = logging.getLogger(__name__)


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
                        "action": "error",
                        "message": (
                            "Voice connection to Gemini dropped. "
                            "Click End, then Start voice to reconnect."
                        ),
                    }
                )


async def handle_stream(websocket: WebSocket, session_id: str) -> None:
    if not settings.gemini_api_key:
        await websocket.close(code=1011, reason="GEMINI_API_KEY is required")
        return

    await websocket.accept()

    pool_session = get_or_create_session(session_id)

    pool_session["websocket"] = websocket
    pool_session["audio_frozen"] = False

    live_session = GeminiLiveSession()
    pool_session["live_session"] = live_session

    try:
        await live_session.connect()
    except Exception as exc:
        logger.exception("Failed to connect Gemini Live session")
        user_message = (
            str(exc)
            if "GEMINI_API_KEY" in str(exc) or "timed out" in str(exc).lower()
            else (
                "Voice service unavailable. Check GEMINI_API_KEY in backend/.env "
                "and your network connection, then click Start voice again."
            )
        )
        with suppress(Exception):
            await websocket.send_json(
                {
                    "type": "control",
                    "action": "error",
                    "message": user_message,
                }
            )
        await websocket.close(code=1011, reason="Gemini Live connection failed")
        return

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
            with suppress(Exception):
                await websocket.send_json(
                    {
                        "type": "ui",
                        "action": "show_products",
                        "payload": {
                            "products": [],
                            "error": "Voice session interrupted. Please reconnect.",
                        },
                    }
                )

    watch_task = asyncio.create_task(_watch_forward())

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
                if ctrl_type == "select_product":
                    product_id = ctrl.get("product_id")
                    if product_id:
                        agent_state = dict(pool_session.get("agent_state") or {})
                        ui_action = dict(agent_state.get("ui_action") or {})
                        payload = dict(ui_action.get("payload") or {})
                        products = payload.get("products") or []
                        selected = next(
                            (p for p in products if p.get("id") == product_id),
                            None,
                        )
                        if selected:
                            if pool_session.get("handoff_running"):
                                logger.info(
                                    "Product tap ignored during handoff for session %s",
                                    session_id,
                                )
                                continue
                            payload["selected_product"] = selected
                            ui_action["payload"] = payload
                            agent_state["ui_action"] = ui_action
                            intent = f"Add {selected.get('name', 'this item')} to cart"
                            prior_messages = list(agent_state.get("messages") or [])
                            try:
                                async with pool_session["graph_lock"]:
                                    result = await get_graph().ainvoke(
                                        {
                                            **agent_state,
                                            "messages": prior_messages
                                            + [HumanMessage(content=intent)],
                                            "voice_mode": True,
                                        },
                                        config={
                                            "configurable": {
                                                "thread_id": pool_session["langgraph_thread_id"]
                                            },
                                            "recursion_limit": 12,
                                        },
                                    )
                                update_agent_state(session_id, result)
                                ui_action = result.get("ui_action") or {}
                                action = ui_action.get("action") or "update_cart"
                                await websocket.send_json(
                                    {
                                        "type": "ui",
                                        "action": action,
                                        "payload": enrich_ui_payload(result),
                                    }
                                )
                                logger.info(
                                    "Added selected product to cart for session %s: %s",
                                    session_id,
                                    selected.get("name"),
                                )
                            except Exception as exc:
                                logger.exception(
                                    "Failed to add selected product for session %s",
                                    session_id,
                                )
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
                continue

            pcm_chunk = message.get("bytes")
            if pcm_chunk is None:
                continue

            if pool_session.get("audio_frozen"):
                continue

            await live_session.send_pcm_audio(pcm_chunk)
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected: %s", session_id)
    finally:
        forward_task.cancel()
        watch_task.cancel()
        with suppress(asyncio.CancelledError):
            await forward_task
        with suppress(asyncio.CancelledError):
            await watch_task
        await live_session.close()
        pool_session["live_session"] = None
        pool_session["websocket"] = None
        pool_session["audio_frozen"] = False
