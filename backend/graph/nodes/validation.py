from __future__ import annotations

from typing import Any

from graph.state import AgentState
from kapruka_mcp.kapruka_tools import kapruka_check_delivery, resolve_delivery_city


def validation_node(state: AgentState) -> dict[str, Any]:
    cart = state.get("cart") or []
    delivery_info = dict(state.get("delivery_info") or {})

    if not cart:
        return {
            "voice_prompt": "Your cart is empty. What would you like to order?",
            "next_node": "discovery",
        }

    city_input = delivery_info.get("city")
    delivery_date = delivery_info.get("date")
    if not city_input or not delivery_date:
        return {
            "voice_prompt": "Please tell me the delivery city and date.",
            "next_node": "end",
        }

    product_id = cart[0]["product_id"]
    canonical_city = resolve_delivery_city(city_input)
    check = kapruka_check_delivery(
        city=canonical_city,
        delivery_date=delivery_date,
        product_id=product_id,
    )

    delivery_info["city"] = canonical_city
    delivery_info["validated"] = "true" if check.get("available") else "false"
    delivery_info["delivery_rate"] = str(check.get("rate", ""))

    if not check.get("available"):
        reason = check.get("reason") or "Delivery is not available for that date."
        next_date = check.get("next_available_date")
        prompt = f"Delivery to {canonical_city} on {delivery_date} isn't available. {reason}"
        if next_date:
            prompt += f" The next available date is {next_date}."
        return {
            "delivery_info": delivery_info,
            "voice_prompt": prompt,
            "next_node": "end",
        }

    perishable_warning = check.get("perishable_warning")
    rate = check.get("rate")
    prompt = (
        f"Good news — Kapruka can deliver to {canonical_city} on {delivery_date} "
        f"for LKR {rate} flat rate."
    )
    if perishable_warning:
        prompt += f" {perishable_warning}"
        return {
            "delivery_info": delivery_info,
            "voice_prompt": prompt,
            "next_node": "end",
        }

    return {
        "delivery_info": delivery_info,
        "voice_prompt": prompt,
        "next_node": "end",
    }
