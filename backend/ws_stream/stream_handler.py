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
from live import session_store
from live.connection_pool import get_or_create_session, update_agent_state
from live.gemini_client import GeminiLiveSession
from live.handoff import run_intent_handoff
from graph.category_catalog import catalog_label
from graph.ui_envelope import enrich_ui_payload
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
    product: dict | None = None,
) -> None:
    agent_state = dict(pool_session.get("agent_state") or {})
    ui_action = dict(agent_state.get("ui_action") or {})
    payload = dict(ui_action.get("payload") or {})
    products = payload.get("products") or []
    selected = next((p for p in products if p.get("id") == product_id), None)
    if selected is None and product and product.get("id") == product_id:
        # Tapped from an earlier carousel that is no longer the active result —
        # use the product the client already has.
        selected = product
    if not selected:
        return

    if pool_session.get("handoff_running"):
        logger.info("Product tap ignored during handoff for session %s", session_id)
        return

    # A tap is an explicit, unambiguous choice. Put it first in the product list so
    # downstream name-matching always resolves to it (not a same-named item in the
    # currently shown results), while keeping the rest for follow-up references.
    others = [p for p in products if p.get("id") != selected.get("id")]
    payload["products"] = [selected, *others]
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


async def _handle_update_cart_item(
    *,
    session_id: str,
    websocket: WebSocket,
    pool_session: dict,
    product_id: str,
    op: str,
) -> None:
    """Increment, decrement, or remove a cart line from the drawer controls."""
    agent_state = dict(pool_session.get("agent_state") or {})
    cart = [dict(item) for item in (agent_state.get("cart") or [])]
    index = next(
        (i for i, item in enumerate(cart) if item.get("product_id") == product_id),
        None,
    )
    if index is None:
        return

    if op == "increment":
        cart[index]["quantity"] = int(cart[index].get("quantity", 1)) + 1
    elif op == "decrement":
        next_qty = int(cart[index].get("quantity", 1)) - 1
        if next_qty <= 0:
            cart.pop(index)
        else:
            cart[index]["quantity"] = next_qty
    elif op == "remove":
        cart.pop(index)
    else:
        return

    delivery_info = dict(agent_state.get("delivery_info") or {})
    if delivery_info.get("validated") == "true":
        delivery_info.pop("validated", None)
        delivery_info.pop("delivery_rate", None)

    agent_state["cart"] = cart
    agent_state["delivery_info"] = delivery_info
    # Editing the cart invalidates any open payment link; keep the snapshot so the
    # UI can flag the stale link until the user requests a fresh one.
    if (agent_state.get("checkout_result") or {}).get("checkout_url"):
        agent_state["checkout_result"] = {}
        agent_state["order_phase"] = "shopping"
    agent_state["ui_action"] = {
        "action": "update_cart",
        "payload": {"cart": cart, "delivery_info": delivery_info},
    }
    update_agent_state(session_id, agent_state)
    await session_store.save_agent_state(session_id, agent_state)

    with suppress(Exception):
        await websocket.send_json(
            {
                "type": "ui",
                "action": "update_cart",
                "payload": enrich_ui_payload(agent_state),
            }
        )
    logger.info("Cart %s for session %s: %s", op, session_id, product_id)


def _validate_submit_checkout(payload: dict) -> str | None:
    recipient = payload.get("recipient") or {}
    sender = payload.get("sender") or {}
    name = str(recipient.get("name") or "").strip()
    phone = str(recipient.get("phone") or "").strip()
    address = str(recipient.get("address") or "").strip()
    sender_name = str(sender.get("name") or "").strip()
    city = str(payload.get("city") or "").strip()
    date = str(payload.get("date") or "").strip()
    if not name:
        return "Please enter the recipient name."
    if not phone:
        return "Please enter the recipient phone number."
    if len(address) < 3:
        return "Please enter a full street address (at least 3 characters)."
    if not sender_name:
        return "Please enter your name as the sender."
    if not city:
        return "Please enter the delivery city."
    if not date:
        return "Please choose a delivery date."
    return None


async def _emit_checkout_form(websocket: WebSocket, agent_state: dict[str, Any]) -> None:
    checkout_info = agent_state.get("checkout_info") or {}
    delivery_info = agent_state.get("delivery_info") or {}
    cart = agent_state.get("cart") or []
    recipient = checkout_info.get("recipient") or {}
    sender = checkout_info.get("sender") or {}
    ready = bool(
        recipient.get("name")
        and recipient.get("phone")
        and len(str(recipient.get("address") or "").strip()) >= 3
        and sender.get("name")
    )
    payload = enrich_ui_payload(
        {
            **agent_state,
            "ui_action": {
                "action": "show_checkout_form",
                "payload": {
                    "checkout_info": checkout_info,
                    "delivery_info": delivery_info,
                    "cart": cart,
                    "ready": ready,
                },
            },
        }
    )
    with suppress(Exception):
        await websocket.send_json(
            {"type": "ui", "action": "show_checkout_form", "payload": payload}
        )


async def _handle_submit_checkout(
    *,
    session_id: str,
    websocket: WebSocket,
    pool_session: dict,
    payload: dict,
) -> None:
    """Confirm the checkout form: merge the (user-reviewed) fields and create the order."""
    recipient = payload.get("recipient") or {}
    sender = payload.get("sender") or {}

    agent_state = dict(pool_session.get("agent_state") or {})
    checkout_info = dict(agent_state.get("checkout_info") or {})
    merged_recipient = dict(checkout_info.get("recipient") or {})
    merged_sender = dict(checkout_info.get("sender") or {})

    for key in ("name", "phone", "address"):
        value = str(recipient.get(key) or "").strip()
        if value:
            merged_recipient[key] = value
    sender_name = str(sender.get("name") or "").strip()
    if sender_name:
        merged_sender["name"] = sender_name

    checkout_info["recipient"] = merged_recipient
    checkout_info["sender"] = merged_sender
    gift_message = str(payload.get("gift_message") or "").strip()
    if gift_message:
        checkout_info["gift_message"] = gift_message

    delivery_info = dict(agent_state.get("delivery_info") or {})
    for key in ("city", "date"):
        value = str(payload.get(key) or "").strip()
        if value:
            delivery_info[key] = value

    agent_state["checkout_info"] = checkout_info
    agent_state["delivery_info"] = delivery_info
    update_agent_state(session_id, agent_state)

    validation_error = _validate_submit_checkout(payload)
    if validation_error:
        await emit_assistant_text(websocket, validation_error)
        await _emit_checkout_form(websocket, agent_state)
        return

    agent_state["checkout_confirmed"] = True
    update_agent_state(session_id, agent_state)

    try:
        result = await run_text_intent(
            session_id=session_id,
            websocket=websocket,
            intent_text="Place order",
            voice_mode=False,
            pool_session=pool_session,
        )
        agent_state = dict(pool_session.get("agent_state") or {})
        checkout_url = (agent_state.get("checkout_result") or {}).get("checkout_url")
        if not checkout_url:
            agent_state["checkout_confirmed"] = False
            update_agent_state(session_id, agent_state)
            await session_store.save_agent_state(session_id, agent_state)
            await _emit_checkout_form(websocket, agent_state)
        elif result:
            logger.info("Checkout confirmed for session %s", session_id)
    except TextIntentBusyError:
        agent_state = dict(pool_session.get("agent_state") or {})
        agent_state["checkout_confirmed"] = False
        update_agent_state(session_id, agent_state)
        await emit_assistant_text(
            websocket,
            "Still working on your last request — please wait a moment.",
        )
    except Exception:
        agent_state = dict(pool_session.get("agent_state") or {})
        agent_state["checkout_confirmed"] = False
        update_agent_state(session_id, agent_state)
        logger.exception("Failed to confirm checkout for session %s", session_id)
        with suppress(Exception):
            await websocket.send_json(
                {
                    "type": "control",
                    "action": "error",
                    "message": "Could not place the order right now. Please try again in a moment.",
                }
            )
        await _emit_checkout_form(websocket, agent_state)


async def _emit_restored_session(websocket: WebSocket, agent_state: dict[str, Any]) -> None:
    """Push cart/delivery/checkout context to the client after Redis or reconnect."""
    if not agent_state:
        return
    cart = agent_state.get("cart") or []
    delivery = agent_state.get("delivery_info") or {}
    checkout = agent_state.get("checkout_info") or {}
    checkout_result = agent_state.get("checkout_result") or {}
    has_delivery = bool(delivery.get("city") or delivery.get("date") or delivery.get("validated"))
    has_checkout_info = bool(checkout.get("recipient") or checkout.get("gift_message"))
    has_payment_link = bool(checkout_result.get("checkout_url"))
    if not cart and not has_delivery and not has_checkout_info and not has_payment_link:
        return
    action = "show_checkout" if has_payment_link else "update_cart"
    payload = enrich_ui_payload({**agent_state, "ui_action": {"action": action, "payload": {}}})
    await websocket.send_json({"type": "ui", "action": action, "payload": payload})


async def handle_stream(websocket: WebSocket, session_id: str) -> None:
    await websocket.accept()

    pool_session = get_or_create_session(session_id)
    pool_session["websocket"] = websocket
    pool_session["audio_frozen"] = False
    pool_session["live_session"] = None
    pool_session["forward_task"] = None
    pool_session["watch_task"] = None

    # Restore persisted state (cart/delivery/checkout) after a restart/redeploy
    # if the in-memory session is fresh and Redis has a snapshot for this id.
    current_state = pool_session.get("agent_state") or {}
    if session_store.is_enabled() and not (current_state.get("cart") or current_state.get("messages")):
        persisted = await session_store.load_agent_state(session_id)
        if persisted:
            pool_session["agent_state"] = persisted
            logger.info("Restored session %s from Redis", session_id)

    agent_state = pool_session.get("agent_state") or {}
    with suppress(Exception):
        await _emit_restored_session(websocket, agent_state)

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
                        provided = ctrl.get("product")
                        await _handle_select_product(
                            session_id=session_id,
                            websocket=websocket,
                            pool_session=pool_session,
                            product_id=product_id,
                            product=provided if isinstance(provided, dict) else None,
                        )
                    continue

                if ctrl_type == "submit_checkout":
                    if pool_session.get("handoff_running"):
                        await emit_assistant_text(
                            websocket,
                            "Still working on your last request — please wait a moment.",
                        )
                        continue
                    await _handle_submit_checkout(
                        session_id=session_id,
                        websocket=websocket,
                        pool_session=pool_session,
                        payload=ctrl,
                    )
                    continue

                if ctrl_type == "set_language":
                    language = str(ctrl.get("language") or "").strip().lower()
                    if language in {"en", "si", "ta"}:
                        agent_state = dict(pool_session.get("agent_state") or {})
                        agent_state["preferred_language"] = language
                        update_agent_state(session_id, agent_state)
                        await session_store.save_agent_state(session_id, agent_state)
                        logger.info("Session %s language set to %s", session_id, language)
                    continue

                if ctrl_type == "update_cart_item":
                    product_id = ctrl.get("product_id")
                    op = ctrl.get("op")
                    if product_id and op:
                        await _handle_update_cart_item(
                            session_id=session_id,
                            websocket=websocket,
                            pool_session=pool_session,
                            product_id=str(product_id),
                            op=str(op),
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
