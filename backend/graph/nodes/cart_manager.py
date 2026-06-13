from __future__ import annotations

from typing import Any

from graph.state import AgentState
from kapruka_mcp.kapruka_tools import extract_price_amount, is_perishable_product


def cart_manager_node(state: AgentState) -> dict[str, Any]:
    payload = (state.get("ui_action") or {}).get("payload") or {}
    selected = payload.get("selected_product")
    if not selected:
        products = payload.get("products") or []
        selected = products[0] if products else None

    if not selected:
        return {
            "voice_prompt": "I don't have a product selected yet. What would you like to add?",
            "next_node": "discovery",
        }

    product_id = selected.get("id") or selected.get("product_id")
    price = extract_price_amount(selected.get("price"))
    if not product_id or price is None:
        return {
            "voice_prompt": "I couldn't read the product details from Kapruka. Let me search again.",
            "next_node": "discovery",
        }

    cart = list(state.get("cart") or [])
    existing = next((item for item in cart if item["product_id"] == product_id), None)
    if existing:
        existing["quantity"] = existing.get("quantity", 1) + 1
    else:
        cart.append(
            {
                "product_id": product_id,
                "quantity": 1,
                "perishable_flag": is_perishable_product(product_id),
                "price": price,
                "name": selected.get("name", ""),
            }
        )

    return {
        "cart": cart,
        "ui_action": {
            "action": "update_cart",
            "payload": {
                **payload,
                "cart": cart,
            },
        },
        "voice_prompt": f"Added {selected.get('name')} to your cart.",
        "next_node": "validation",
    }
