from __future__ import annotations

import logging
import re
from typing import Any

from langchain_core.messages import HumanMessage

from graph.llm import get_llm
from graph.product_pick import (
    extract_browse_search_query,
    extract_followup_search_query,
    is_delivery_followup,
    normalize_search_query,
    pick_product_from_text,
    product_match_score,
    resolve_search_query,
    route_cart_add_node,
    should_add_to_cart,
    wants_add_product,
    _is_browse_search_intent,
)
from graph.state import AgentState, RouterDecision

logger = logging.getLogger(__name__)

DATE_PATTERN = re.compile(r"\b(20\d{2}-\d{2}-\d{2})\b")
# City/date parsing uses the last " to … on YYYY-MM-DD" segment (avoids matching "want to").
SEARCH_QUERY_PATTERN = re.compile(
    r"\bsend(?:\s+a|\s+an)?\s+(.+?)\s+to\s+.+?\s+on\s+20\d{2}-\d{2}-\d{2}\b",
    re.IGNORECASE,
)
CHECKOUT_INTENT_PATTERN = re.compile(
    r"\b(checkout|check out|place order|confirm order|create order|pay now|proceed to pay|"
    r"complete order|payment link|order now|ready to pay|send the link|get the link)\b",
    re.IGNORECASE,
)
# "pay" alone is too broad (e.g. "how do I pay") — require explicit pay intent.
PAY_INTENT_PATTERN = re.compile(
    r"\b(pay|paying|i(?:'ll| will) pay|want to pay|like to pay)\b",
    re.IGNORECASE,
)
ADD_PRODUCT_PATTERN = re.compile(
    r"\b(another|add more|also (?:add|get|send)|something else|search (?:for|again)|"
    r"flowers too|add flowers|plus a|as well)\b",
    re.IGNORECASE,
)
GIFT_MESSAGE_PATTERN = re.compile(
    r"(?:gift message|message on (?:the )?card|card message|wish(?:es)?|"
    r"say on the card)[:\s]+(.{1,300})",
    re.IGNORECASE,
)
PHONE_PATTERN = re.compile(r"(?:\+94|0)?7\d{8}")


def _latest_user_text(state: AgentState) -> str:
    for message in reversed(state["messages"]):
        if isinstance(message, HumanMessage):
            return str(message.content)
    return ""


def _wants_more_products(user_text: str) -> bool:
    return bool(ADD_PRODUCT_PATTERN.search(user_text))


def _wants_checkout(user_text: str) -> bool:
    return bool(CHECKOUT_INTENT_PATTERN.search(user_text) or PAY_INTENT_PATTERN.search(user_text))


def _mentions_checkout_details(user_text: str) -> bool:
    """True when the user may be providing recipient/sender info (not a delivery city/date turn)."""
    if PHONE_PATTERN.search(user_text):
        return True
    if DATE_PATTERN.search(user_text) and not re.search(
        r"(?i)\b(recipient|receiver|sender|phone|mobile|contact|address|street|"
        r"my name is|i am|i'm|name is|named)\b",
        user_text,
    ):
        return False
    return bool(
        re.search(
            r"\b(recipient|receiver|sender|phone|mobile|"
            r"contact|address|street|my name is|i am|i'm|name is|named)\b",
            user_text,
            re.IGNORECASE,
        )
    )


def _is_placeholder_address(address: str) -> bool:
    normalized = address.strip().lower()
    return normalized in {"", "address tbd", "tbd", "n/a", "na", "unknown"}


def _merge_checkout_info(
    existing: dict[str, Any],
    *,
    recipient_name: str | None,
    recipient_phone: str | None,
    recipient_address: str | None,
    sender_name: str | None,
    gift_message: str | None,
) -> dict[str, Any]:
    checkout_info = dict(existing)
    recipient = dict(checkout_info.get("recipient") or {})
    sender = dict(checkout_info.get("sender") or {})

    if recipient_name:
        recipient["name"] = recipient_name
    if recipient_phone:
        recipient["phone"] = recipient_phone
    if recipient_address and not _is_placeholder_address(recipient_address):
        recipient["address"] = recipient_address.strip()
    if sender_name:
        sender["name"] = sender_name

    if recipient:
        checkout_info["recipient"] = recipient
    if sender:
        checkout_info["sender"] = sender
    if gift_message:
        checkout_info["gift_message"] = gift_message

    return checkout_info


def _has_checkout_details(checkout_info: dict[str, Any]) -> bool:
    recipient = checkout_info.get("recipient") or {}
    sender = checkout_info.get("sender") or {}
    address = str(recipient.get("address") or "").strip()
    return bool(
        recipient.get("name")
        and recipient.get("phone")
        and sender.get("name")
        and address
        and not _is_placeholder_address(address)
    )


def _extract_checkout_from_text(user_text: str, checkout_info: dict[str, Any]) -> dict[str, Any]:
    """Lightweight regex extraction before/alongside LLM routing."""
    recipient_name = None
    recipient_phone = None
    recipient_address = None
    sender_name = None
    gift_message = None

    gift_match = GIFT_MESSAGE_PATTERN.search(user_text)
    if gift_match:
        gift_message = gift_match.group(1).strip().rstrip(".,;")

    phone_match = PHONE_PATTERN.search(user_text)
    if phone_match:
        recipient_phone = phone_match.group(0)

    sender_match = re.search(
        r"(?:sender|from|my name is|i am|i'm)(?:\s+is)?\s+([A-Za-z][A-Za-z\s'.-]{1,40})",
        user_text,
        re.IGNORECASE,
    )
    if sender_match:
        sender_name = sender_match.group(1).strip().rstrip(".,;")

    recipient_match = re.search(
        r"(?:recipient|receiver|deliver to|send to|for)(?:\s+is)?\s+([A-Za-z][A-Za-z\s'.-]{1,40})",
        user_text,
        re.IGNORECASE,
    )
    if recipient_match:
        recipient_name = recipient_match.group(1).strip().rstrip(".,;")
        # Trim trailing "phone/mobile ..." if captured.
        recipient_name = re.split(
            r"\b(?:phone|mobile|number|contact)\b",
            recipient_name,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0].strip()

    if not recipient_name:
        name_match = re.search(
            r"(?:name is|named)\s+([A-Za-z][A-Za-z\s'.-]{1,40})",
            user_text,
            re.IGNORECASE,
        )
        if name_match and not sender_match:
            recipient_name = name_match.group(1).strip().rstrip(".,;")

    address_match = re.search(
        r"(?:address|delivery address|street(?: address)?)(?:\s+is)?\s*[:\-]?\s*(.{5,120})",
        user_text,
        re.IGNORECASE,
    )
    if address_match:
        recipient_address = address_match.group(1).strip().rstrip(".,;")
        recipient_address = re.split(
            r"\b(?:phone|mobile|sender|recipient)\b",
            recipient_address,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0].strip()

    if not recipient_address:
        street_match = re.search(
            r"(?:phone|mobile|number|contact)\s*[:\s]*(?:\+94|0)?7\d{8}\s*[,;]\s*(.{5,120}?)"
            r"(?:,\s*(?:from|sender|recipient)\b|$)",
            user_text,
            re.IGNORECASE,
        )
        if street_match:
            candidate = street_match.group(1).strip().rstrip(".,;")
            if re.search(r"\d", candidate) and not _is_placeholder_address(candidate):
                recipient_address = candidate

    return _merge_checkout_info(
        checkout_info,
        recipient_name=recipient_name,
        recipient_phone=recipient_phone,
        recipient_address=recipient_address,
        sender_name=sender_name,
        gift_message=gift_message,
    )


def _deterministic_next(state: AgentState, user_text: str) -> str | None:
    cart = state.get("cart") or []
    ui_action = state.get("ui_action") or {}
    payload = ui_action.get("payload") or {}
    products = payload.get("products") or []
    selected = payload.get("selected_product")
    delivery_info = state.get("delivery_info") or {}
    checkout_info = state.get("checkout_info") or {}
    validated = delivery_info.get("validated") == "true"
    has_products = bool(products)

    new_query = resolve_search_query(
        user_text,
        products=products,
        selected_product=selected,
        cart=cart,
    )
    shown_query = normalize_search_query(str(payload.get("search_query") or ""))

    if new_query and normalize_search_query(new_query) != shown_query:
        return "discovery"

    cart_route = route_cart_add_node(
        user_text,
        products,
        cart,
        selected_product=selected,
    )
    if cart_route:
        return cart_route

    if not has_products and not cart:
        return "discovery"
    if has_products and not cart:
        return "end"
    if cart and delivery_info.get("city") and delivery_info.get("date"):
        validated_flag = delivery_info.get("validated")
        if validated_flag == "false":
            return "end"
        if validated_flag != "true":
            return "validation"
    elif cart and not (delivery_info.get("city") and delivery_info.get("date")):
        return "end"
    if cart and delivery_info.get("validated") == "true":
        if _has_checkout_details(checkout_info):
            return "checkout"
        return "end"
    return None


def _extract_delivery_from_text(user_text: str) -> dict[str, str]:
    delivery: dict[str, str] = {}
    date_match = DATE_PATTERN.search(user_text)
    if not date_match:
        return delivery

    delivery["date"] = date_match.group(1)
    prefix = user_text[: date_match.start()].strip()

    # Full sentence: "... to CITY on ..."
    to_idx = prefix.lower().rfind(" to ")
    if to_idx != -1:
        city_part = prefix[to_idx + len(" to ") :]
        on_idx = city_part.lower().rfind(" on ")
        if on_idx != -1:
            city_part = city_part[:on_idx]
        city_part = re.sub(r"(?i)\s+on\s*$", "", city_part)
        city = city_part.strip(" ,.")
        if city:
            delivery["city"] = city
            return delivery

    # Short follow-up: "Kadawatha on 2026-06-25" or "delivery Kadawatha"
    on_idx = prefix.lower().rfind(" on ")
    if on_idx != -1:
        city = prefix[:on_idx].strip(" ,.")
    else:
        city = prefix.strip(" ,.")
        city = re.sub(r"(?i)\s+on\s*$", "", city).strip(" ,.")
    city = re.sub(
        r"(?i)^(please\s+)?(deliver(?:y)?(?: to)?|send(?: to)?|ship(?: to)?|city|location)\s+",
        "",
        city,
    ).strip(" ,.")
    if city and not re.search(
        r"(?i)\b(checkout|recipient|sender|phone|mobile|address|name is)\b",
        city,
    ):
        delivery["city"] = city
    return delivery


def _extract_search_query(user_text: str) -> str | None:
    match = SEARCH_QUERY_PATTERN.search(user_text)
    if match:
        return match.group(1).strip()
    return None


def _apply_router_decision(
    *,
    decision: RouterDecision,
    state: AgentState,
    delivery_info: dict[str, str],
    ui_action: dict[str, Any],
    checkout_info: dict[str, Any],
) -> dict[str, Any]:
    prior_city = delivery_info.get("city")
    prior_date = delivery_info.get("date")
    if decision.delivery_city:
        delivery_info["city"] = decision.delivery_city
    if decision.delivery_date:
        delivery_info["date"] = decision.delivery_date
    if decision.delivery_city and decision.delivery_city != prior_city:
        delivery_info.pop("validated", None)
        delivery_info.pop("delivery_rate", None)
    if decision.delivery_date and decision.delivery_date != prior_date:
        delivery_info.pop("validated", None)
        delivery_info.pop("delivery_rate", None)

    checkout_info = _merge_checkout_info(
        checkout_info,
        recipient_name=decision.recipient_name,
        recipient_phone=decision.recipient_phone,
        recipient_address=decision.recipient_address,
        sender_name=decision.sender_name,
        gift_message=decision.gift_message,
    )

    cart = state.get("cart") or []
    validated = delivery_info.get("validated") == "true"
    next_node = decision.next_node

    if cart and validated and _has_checkout_details(checkout_info):
        next_node = "checkout"
    elif cart and validated and (decision.wants_checkout or _wants_checkout(_latest_user_text(state))):
        next_node = "end"

    updates: dict[str, Any] = {
        "next_node": next_node or "discovery",
        "delivery_info": delivery_info,
        "checkout_info": checkout_info,
    }
    if decision.voice_prompt:
        updates["voice_prompt"] = decision.voice_prompt
    if decision.search_query:
        payload = dict((ui_action.get("payload") or {}))
        payload["search_query"] = decision.search_query
        updates["ui_action"] = {
            "action": ui_action.get("action", ""),
            "payload": payload,
        }

    if next_node == "end" and cart and validated and not _has_checkout_details(checkout_info):
        if decision.wants_checkout or _wants_checkout(_latest_user_text(state)):
            updates["voice_prompt"] = (
                "Delivery looks good, but I still need the recipient name, phone, and street address, "
                "plus your name as the sender, before I can create the Kapruka checkout link."
            )

    return updates


def _llm_route(state: AgentState, user_text: str) -> RouterDecision:
    llm = get_llm().with_structured_output(RouterDecision)
    cart = state.get("cart") or []
    validated = (state.get("delivery_info") or {}).get("validated") == "true"
    return llm.invoke(
        [
            {
                "role": "system",
                "content": (
                    "You route a Kapruka shopping agent. Extract delivery city, delivery date "
                    "(YYYY-MM-DD), product search query, and checkout details when relevant. "
                    "Set wants_checkout=true when the user asks to place/pay/checkout the order. "
                    "Extract gift_message when the user gives card text for the recipient. "
                    "Accept Sinhala, Tamil, Tanglish, and English — normalize dates to YYYY-MM-DD "
                    "in delivery_date but preserve names/messages in the user's language. "
                    "Set next_node to checkout ONLY when cart exists, delivery is validated, and "
                    "recipient name, recipient phone, recipient street address, and sender name "
                    "are all known. Never set next_node to checkout without those details. "
                    "Do NOT claim an order was created — checkout only prepares a payment link."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"User message: {user_text}\n"
                    f"Cart items: {len(cart)}\n"
                    f"Delivery validated: {validated}\n"
                    f"Existing checkout info: {state.get('checkout_info') or {}}"
                ),
            },
        ]
    )


def router_node(state: AgentState) -> dict[str, Any]:
    user_text = _latest_user_text(state)
    delivery_info = dict(state.get("delivery_info") or {})
    extracted = _extract_delivery_from_text(user_text)
    if extracted.get("city") and extracted.get("city") != delivery_info.get("city"):
        delivery_info.pop("validated", None)
        delivery_info.pop("delivery_rate", None)
    if extracted.get("date") and extracted.get("date") != delivery_info.get("date"):
        delivery_info.pop("validated", None)
        delivery_info.pop("delivery_rate", None)
    delivery_info.update({k: v for k, v in extracted.items() if v})

    checkout_info = _extract_checkout_from_text(
        user_text,
        dict(state.get("checkout_info") or {}),
    )

    ui_action = dict(state.get("ui_action") or {})
    payload = dict(ui_action.get("payload") or {})
    cart = state.get("cart") or []
    search_query = _extract_search_query(user_text) or resolve_search_query(
        user_text,
        products=payload.get("products") or [],
        selected_product=payload.get("selected_product"),
        cart=cart or None,
    )
    if search_query and not is_delivery_followup(user_text, cart=cart):
        payload["search_query"] = search_query
        ui_action["payload"] = payload

    merged_state = {**state, "delivery_info": delivery_info, "checkout_info": checkout_info}
    cart = merged_state.get("cart") or []
    validated = delivery_info.get("validated") == "true"
    products = payload.get("products") or []
    selected = payload.get("selected_product")
    shown_query = normalize_search_query(str(payload.get("search_query") or ""))
    pending_query = resolve_search_query(
        user_text,
        products=products,
        selected_product=selected,
        cart=cart or None,
    )

    # Delivery validation — before new product search when cart has city/date.
    if (
        cart
        and delivery_info.get("city")
        and delivery_info.get("date")
        and delivery_info.get("validated") != "true"
        and not _wants_checkout(user_text)
    ):
        logger.info("Router delivery follow-up -> validation for %s", delivery_info.get("city"))
        return {
            "next_node": "validation",
            "delivery_info": delivery_info,
            "checkout_info": checkout_info,
            "ui_action": ui_action,
        }

    # New catalog search while the cart already has items (e.g. "I want flowers").
    if (
        cart
        and pending_query
        and normalize_search_query(pending_query) != shown_query
        and not _wants_checkout(user_text)
        and not _mentions_checkout_details(user_text)
    ):
        payload["search_query"] = pending_query
        payload.pop("selected_product", None)
        payload.pop("products", None)
        ui_action["payload"] = payload
        ui_action["action"] = "show_products"
        logger.info("Router new search with cart -> discovery (%s)", pending_query)
        return {
            "next_node": "discovery",
            "delivery_info": delivery_info,
            "checkout_info": checkout_info,
            "ui_action": ui_action,
        }

    # Add another item — pick from on-screen carousel or run a new search.
    if cart and not _wants_checkout(user_text) and not _mentions_checkout_details(user_text):
        picked = pick_product_from_text(user_text, products)
        if picked and should_add_to_cart(
            user_text,
            products,
            selected_product=picked,
        ):
            picked_id = picked.get("id") or picked.get("product_id")
            already_in_cart = any(item["product_id"] == picked_id for item in cart)
            if not already_in_cart:
                payload["selected_product"] = picked
                ui_action["payload"] = payload
                logger.info("Router add from carousel -> %s", picked.get("name"))
                return {
                    "next_node": "cart_manager",
                    "delivery_info": delivery_info,
                    "checkout_info": checkout_info,
                    "ui_action": ui_action,
                }

        if wants_add_product(user_text) or _wants_more_products(user_text):
            followup = resolve_search_query(
                user_text,
                products=products,
                selected_product=payload.get("selected_product"),
                cart=cart or None,
            ) or search_query
            carousel_pick = pick_product_from_text(user_text, products)
            if (
                followup
                and normalize_search_query(followup) != normalize_search_query(payload.get("search_query"))
                and not carousel_pick
            ):
                payload["search_query"] = followup
                payload.pop("products", None)
                payload.pop("selected_product", None)
                ui_action["payload"] = payload
                ui_action["action"] = "show_products"
                logger.info("Router add via new search -> discovery")
                return {
                    "next_node": "discovery",
                    "delivery_info": delivery_info,
                    "checkout_info": checkout_info,
                    "ui_action": ui_action,
                }

    # Fast path: regex already has everything — skip LLM and create the payment link.
    if cart and validated and _has_checkout_details(checkout_info):
        logger.info("Router routing to checkout (regex details): %s", checkout_info)
        return {
            "next_node": "checkout",
            "delivery_info": delivery_info,
            "checkout_info": checkout_info,
        }

    # Checkout turn: user asked to pay or is providing recipient/sender details.
    if cart and validated and (_wants_checkout(user_text) or _mentions_checkout_details(user_text)):
        decision = _llm_route(merged_state, user_text)
        updates = _apply_router_decision(
            decision=decision,
            state=merged_state,
            delivery_info=delivery_info,
            ui_action=ui_action,
            checkout_info=checkout_info,
        )
        logger.info(
            "Router checkout turn -> next_node=%s checkout_info=%s",
            updates.get("next_node"),
            updates.get("checkout_info"),
        )
        return updates

    deterministic = _deterministic_next(merged_state, user_text)
    if deterministic:
        updates: dict[str, Any] = {
            "next_node": deterministic,
            "delivery_info": delivery_info,
            "checkout_info": checkout_info,
        }
        state_ui = state.get("ui_action") or {}
        if state_ui.get("action") == "show_products":
            updates["ui_action"] = state_ui
        elif search_query:
            updates["ui_action"] = ui_action
        if deterministic == "end":
            if state.get("voice_prompt") and (state.get("ui_action") or {}).get("action") == "show_products":
                updates["voice_prompt"] = state["voice_prompt"]
            elif products and not cart:
                updates["voice_prompt"] = (
                    "Browse the options on screen — tap your favourite or tell me which one to add."
                )
            elif cart and not validated and not (delivery_info.get("city") and delivery_info.get("date")):
                if (state.get("ui_action") or {}).get("action") != "show_products":
                    updates["voice_prompt"] = (
                        "Your cart is ready — open the cart icon to review. "
                        "Tell me a delivery city and date (for example, Kadawatha on 2026-06-25), "
                        "say if you'd like more gifts, or say checkout when you're ready."
                    )
            elif cart and validated and not _has_checkout_details(checkout_info) and _wants_checkout(user_text):
                updates["voice_prompt"] = (
                    "To create your Kapruka payment link, tell me the recipient name, phone, and "
                    "street address, plus your name as the sender."
                )
            elif state.get("voice_prompt"):
                updates["voice_prompt"] = state["voice_prompt"]
        elif deterministic == "checkout":
            logger.info("Router routing to checkout with details: %s", checkout_info)
        return updates

    if state.get("voice_mode"):
        cart = merged_state.get("cart") or []
        payload = (merged_state.get("ui_action") or {}).get("payload") or {}
        if (
            cart
            and delivery_info.get("city")
            and delivery_info.get("date")
            and delivery_info.get("validated") != "true"
            and not _wants_checkout(user_text)
        ):
            return {
                "next_node": "validation",
                "delivery_info": delivery_info,
                "checkout_info": checkout_info,
                "ui_action": ui_action,
            }
        if (
            pending_query
            and normalize_search_query(pending_query) != shown_query
            and not _wants_checkout(user_text)
            and not is_delivery_followup(user_text, cart=cart or None)
        ):
            payload = dict(payload)
            payload["search_query"] = pending_query
            payload.pop("selected_product", None)
            payload.pop("products", None)
            ui_action["payload"] = payload
            ui_action["action"] = "show_products"
            return {
                "next_node": "discovery",
                "delivery_info": delivery_info,
                "checkout_info": checkout_info,
                "ui_action": ui_action,
            }
        if cart or payload.get("products"):
            return {
                "next_node": "end",
                "delivery_info": delivery_info,
                "checkout_info": checkout_info,
                "voice_prompt": (
                    "Tell me the delivery city and date, or say checkout with recipient details "
                    "when you're ready."
                ),
            }
        return {
            "next_node": "discovery",
            "delivery_info": delivery_info,
            "checkout_info": checkout_info,
            **({"ui_action": ui_action} if search_query else {}),
        }

    decision = _llm_route(merged_state, user_text)
    return _apply_router_decision(
        decision=decision,
        state=merged_state,
        delivery_info=delivery_info,
        ui_action=ui_action,
        checkout_info=checkout_info,
    )
