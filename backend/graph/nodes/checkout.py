from __future__ import annotations

import logging
from typing import Any

from graph.state import AgentState
from kapruka_mcp.kapruka_tools import KaprukaMCPError, kapruka_create_order

logger = logging.getLogger(__name__)

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
    if not address or address.lower() in {"address tbd", "tbd", "n/a"}:
        return {
            "voice_prompt": (
                "I still need the recipient's street address for delivery before I can "
                "create the Kapruka payment link."
            ),
            "next_node": "end",
        }

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
        return {
            "voice_prompt": f"I couldn't create the Kapruka checkout link. {message}",
            "next_node": "end",
        }

    checkout_url = order.get("checkout_url")
    if not checkout_url:
        return {
            "voice_prompt": "Kapruka did not return a checkout link. Please try checkout again.",
            "next_node": "end",
        }

    logger.info("kapruka_create_order succeeded: %s", checkout_url)

    return {
        "ui_action": {
            "action": "show_checkout",
            "payload": {
                "checkout_url": checkout_url,
                "order_ref": order.get("order_ref"),
                "summary": order.get("summary"),
                "expires_at": order.get("expires_at"),
            },
        },
        "voice_prompt": (
            "I've created your Kapruka guest checkout link. Open it to pay within 60 minutes. "
            "The reference on screen is for checkout only — your real Kapruka order number "
            "arrives by email after you pay. On the payment page, scroll to Summary if the "
            "top says zero items; your cake should be listed there."
        ),
        "next_node": "end",
    }
