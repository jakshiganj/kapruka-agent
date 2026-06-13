from __future__ import annotations

from typing import Any

from graph.state import AgentState
from kapruka_mcp.kapruka_tools import kapruka_create_order


def checkout_node(state: AgentState) -> dict[str, Any]:
    cart = state.get("cart") or []
    delivery_info = state.get("delivery_info") or {}
    checkout_info = state.get("checkout_info") or {}

    recipient = checkout_info.get("recipient") or {}
    sender = checkout_info.get("sender") or {}
    gift_message = checkout_info.get("gift_message", "")

    if not cart or not recipient or not sender:
        return {
            "voice_prompt": "I need recipient and sender details before checkout.",
            "next_node": "end",
        }

    delivery = {
        "address": recipient.get("address") or delivery_info.get("address") or "Address TBD",
        "city": delivery_info.get("city", ""),
        "date": delivery_info.get("date", ""),
        "location_type": delivery_info.get("location_type", "house"),
        "instructions": delivery_info.get("instructions"),
    }

    mcp_cart = [
        {"product_id": item["product_id"], "quantity": item.get("quantity", 1)}
        for item in cart
    ]

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

    return {
        "ui_action": {
            "action": "show_checkout",
            "payload": {
                "checkout_url": order.get("checkout_url"),
                "order_ref": order.get("order_ref"),
                "summary": order.get("summary"),
                "expires_at": order.get("expires_at"),
            },
        },
        "voice_prompt": (
            "Your order is ready. Open the checkout link to complete payment within 60 minutes."
        ),
        "next_node": "end",
    }
