from __future__ import annotations

import logging
from typing import Any

from graph.order_lifecycle import mark_link_ready
from graph.state import AgentState
from kapruka_mcp.kapruka_tools import KaprukaMCPError, kapruka_create_order

logger = logging.getLogger(__name__)

MIN_ADDRESS_LEN = 3


def _valid_address(address: str) -> bool:
    cleaned = address.strip()
    if len(cleaned) < MIN_ADDRESS_LEN:
        return False
    return cleaned.lower() not in {"address tbd", "tbd", "n/a"}


def _checkout_form_ready(checkout_info: dict[str, Any]) -> bool:
    recipient = checkout_info.get("recipient") or {}
    sender = checkout_info.get("sender") or {}
    return bool(
        recipient.get("name")
        and recipient.get("phone")
        and _valid_address(str(recipient.get("address") or ""))
        and sender.get("name")
    )


def _checkout_form_ui(
    *,
    cart: list[dict[str, Any]],
    delivery_info: dict[str, Any],
    checkout_info: dict[str, Any],
) -> dict[str, Any]:
    return {
        "action": "show_checkout_form",
        "payload": {
            "checkout_info": checkout_info,
            "delivery_info": delivery_info,
            "cart": cart,
            "ready": _checkout_form_ready(checkout_info),
        },
    }


def _checkout_error_response(
    *,
    cart: list[dict[str, Any]],
    delivery_info: dict[str, Any],
    checkout_info: dict[str, Any],
    voice_prompt: str,
) -> dict[str, Any]:
    return {
        "checkout_confirmed": False,
        "delivery_info": delivery_info,
        "checkout_info": checkout_info,
        "voice_prompt": voice_prompt,
        "next_node": "end",
        "ui_action": _checkout_form_ui(
            cart=cart,
            delivery_info=delivery_info,
            checkout_info=checkout_info,
        ),
    }


def _is_delivery_network_error(message: str) -> bool:
    lower = message.lower()
    return any(
        token in lower
        for token in (
            "city_not_deliverable",
            "city_not_found",
            "not in kapruka",
            "unknown city",
            "delivery network",
        )
    )


def checkout_node(state: AgentState) -> dict[str, Any]:
    cart = state.get("cart") or []
    delivery_info = state.get("delivery_info") or {}
    checkout_info = state.get("checkout_info") or {}

    recipient = checkout_info.get("recipient") or {}
    sender = checkout_info.get("sender") or {}
    gift_message = checkout_info.get("gift_message", "")

    if not cart:
        return {
            "voice_prompt": "Your cart is empty. What would you like to order?",
            "next_node": "discovery",
        }

    if delivery_info.get("validated") != "true":
        return {
            "voice_prompt": "Let me confirm delivery availability before checkout.",
            "next_node": "validation",
        }

    if not recipient.get("name") or not recipient.get("phone") or not sender.get("name"):
        return {
            "voice_prompt": (
                "I need the recipient name and phone, plus your name as sender, "
                "before I can create the Kapruka checkout link."
            ),
            "next_node": "end",
        }

    address = str(recipient.get("address") or delivery_info.get("address") or "").strip()
    if not _valid_address(address):
        return _checkout_error_response(
            cart=cart,
            delivery_info=delivery_info,
            checkout_info=checkout_info,
            voice_prompt=(
                "I still need the recipient's full street address for delivery "
                f"(at least {MIN_ADDRESS_LEN} characters) before I can create the Kapruka payment link."
            ),
        )

    delivery = {
        "address": address,
        "city": delivery_info.get("city", ""),
        "date": delivery_info.get("date", ""),
        "location_type": delivery_info.get("location_type", "house"),
        "instructions": delivery_info.get("instructions"),
    }

    mcp_cart = [
        {"product_id": item["product_id"], "quantity": item.get("quantity", 1)}
        for item in cart
    ]

    try:
        logger.info(
            "Calling kapruka_create_order cart=%s recipient=%s city=%s",
            mcp_cart,
            recipient.get("name"),
            delivery.get("city"),
        )
        order = kapruka_create_order(
            cart=mcp_cart,
            recipient={
                "name": recipient.get("name", ""),
                "phone": recipient.get("phone", ""),
            },
            delivery=delivery,
            sender={
                "name": sender.get("name", ""),
                "anonymous": sender.get("anonymous", False),
            },
            gift_message=gift_message or None,
        )
    except KaprukaMCPError as exc:
        message = str(exc).removeprefix("Error:").strip()
        updated_delivery = dict(delivery_info)
        if _is_delivery_network_error(message):
            updated_delivery["validated"] = "false"
            updated_delivery.pop("delivery_rate", None)
        return _checkout_error_response(
            cart=cart,
            delivery_info=updated_delivery,
            checkout_info=checkout_info,
            voice_prompt=f"I couldn't create the Kapruka checkout link. {message}",
        )

    checkout_url = order.get("checkout_url") or order.get("checkoutUrl") or order.get("payment_url")
    if not checkout_url:
        return {
            "voice_prompt": "Kapruka did not return a checkout link. Please try checkout again.",
            "next_node": "end",
        }

    logger.info("kapruka_create_order succeeded: %s", checkout_url)

    checkout_result = {
        "checkout_url": checkout_url,
        "order_ref": order.get("order_ref") or order.get("orderRef"),
        "summary": order.get("summary"),
        "expires_at": order.get("expires_at") or order.get("expiresAt"),
    }

    return {
        **mark_link_ready(cart),
        "checkout_result": checkout_result,
        "checkout_confirmed": False,
        "ui_action": {
            "action": "show_checkout",
            "payload": checkout_result,
        },
        "voice_prompt": (
            f"Your Kapruka payment link is ready — open it to pay within 60 minutes: {checkout_url} "
            "The reference on screen is for checkout only — your real Kapruka order number "
            "arrives by email after you pay. On the payment page, scroll to Summary if the "
            "top says zero items; your cake should be listed there."
        ),
        "next_node": "end",
    }
