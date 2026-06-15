from __future__ import annotations

from typing import Any

from graph.order_lifecycle import checkout_link_ready, invalidate_checkout
from graph.state import AgentState
from graph.product_pick import pick_product_from_text
from kapruka_mcp.kapruka_tools import extract_price_amount, is_perishable_product


def _latest_user_text(state: AgentState) -> str:
    from langchain_core.messages import HumanMessage

    for message in reversed(state["messages"]):
        if isinstance(message, HumanMessage):
            return str(message.content)
    return ""


def cart_manager_node(state: AgentState) -> dict[str, Any]:
    payload = (state.get("ui_action") or {}).get("payload") or {}
    products = payload.get("products") or []
    user_text = _latest_user_text(state)

    selected = payload.get("selected_product")
    if products:
        picked = pick_product_from_text(user_text, products)
        if picked:
            selected = picked
    if not selected:
        return {
            "voice_prompt": (
                "Which gift would you like? Tap one on screen or tell me the name — "
                "for example, the Lavender Love cake."
            ),
            "next_node": "end",
        }

    product_id = selected.get("id") or selected.get("product_id")
    price = extract_price_amount(selected.get("price"))
    if not product_id or price is None:
        return {
            "voice_prompt": "I couldn't read the product details from Kapruka. Let me search again.",
            "next_node": "discovery",
        }

    cart = list(state.get("cart") or [])
    delivery_info = dict(state.get("delivery_info") or {})
    had_checkout_link = checkout_link_ready(state)
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
                "image_url": selected.get("image_url"),
            }
        )

    if delivery_info.get("validated") == "true":
        delivery_info.pop("validated", None)

    result: dict[str, Any] = {
        "cart": cart,
        "delivery_info": delivery_info,
        "ui_action": {
            "action": "update_cart",
            "payload": {
                **payload,
                "cart": cart,
            },
        },
        "voice_prompt": _after_add_prompt(
            selected.get("name", "item"),
            delivery_info,
            had_checkout_link=had_checkout_link,
        ),
        "next_node": "validation" if delivery_info.get("city") and delivery_info.get("date") else "end",
    }
    if had_checkout_link:
        result.update(invalidate_checkout(state))
    return result


def _after_add_prompt(
    name: str,
    delivery_info: dict[str, Any],
    *,
    had_checkout_link: bool = False,
) -> str:
    if had_checkout_link:
        if delivery_info.get("city") and delivery_info.get("date"):
            return (
                f"Added {name}. Your previous payment link was for the old cart — "
                f"I'll re-check delivery to {delivery_info['city']}, then say checkout "
                "when you're ready for a fresh payment link."
            )
        return (
            f"Added {name}. Your previous payment link was for the old cart — "
            "say checkout when you're ready and I'll generate a fresh payment link."
        )
    if delivery_info.get("city") and delivery_info.get("date"):
        return f"Added {name} to your cart. I'll check delivery to {delivery_info['city']} next."
    return (
        f"Added {name} to your cart — tap the cart icon to review. "
        "Would you like to browse more gifts, or shall we proceed to checkout?"
    )
