"""Enrich UI JSON payloads with full session context for the frontend."""

from __future__ import annotations

from typing import Any


def enrich_ui_payload(result: dict[str, Any]) -> dict[str, Any]:
    """Merge cart, delivery, checkout context, and payment link into every UI envelope."""
    ui_action = result.get("ui_action") or {}
    action = ui_action.get("action")
    raw_payload = ui_action.get("payload") or {}
    payload = dict(raw_payload)
    payload["cart"] = result.get("cart") or []
    payload["delivery_info"] = result.get("delivery_info") or {}
    payload["checkout_info"] = result.get("checkout_info") or {}

    if action == "show_products" or raw_payload.get("products"):
        payload["products"] = raw_payload.get("products") or []
        if raw_payload.get("search_query") is not None:
            payload["search_query"] = raw_payload.get("search_query")

    checkout_result = result.get("checkout_result") or {}
    for key in ("checkout_url", "order_ref", "summary", "expires_at"):
        if checkout_result.get(key) is not None:
            payload[key] = checkout_result[key]

    return payload
