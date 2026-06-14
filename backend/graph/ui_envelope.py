"""Enrich UI JSON payloads with full session context for the frontend."""

from __future__ import annotations

from typing import Any

from graph.order_lifecycle import is_checkout_stale, normalize_cart_line


def _snapshot_summary(snapshot: list[dict[str, Any]]) -> dict[str, Any]:
    lines = [normalize_cart_line(item) for item in snapshot]
    return {
        "item_count": sum(qty for _, qty in lines),
        "product_ids": [product_id for product_id, _ in lines],
        "lines": [
            {"product_id": product_id, "quantity": quantity}
            for product_id, quantity in lines
        ],
    }


def enrich_ui_payload(result: dict[str, Any]) -> dict[str, Any]:
    """Merge cart, delivery, checkout context, and payment link into every UI envelope."""
    ui_action = result.get("ui_action") or {}
    action = ui_action.get("action")
    raw_payload = ui_action.get("payload") or {}
    payload = dict(raw_payload)
    payload["cart"] = result.get("cart") or []
    payload["delivery_info"] = result.get("delivery_info") or {}
    payload["checkout_info"] = result.get("checkout_info") or {}

    order_phase = result.get("order_phase") or raw_payload.get("order_phase") or "shopping"
    payload["order_phase"] = order_phase

    snapshot = result.get("checkout_cart_snapshot") or []
    if snapshot:
        payload["checkout_cart_snapshot"] = _snapshot_summary(snapshot)

    stale = is_checkout_stale(result)
    if stale:
        payload["checkout_stale"] = True
    elif action == "show_checkout":
        payload["checkout_stale"] = False

    if action == "show_categories" or raw_payload.get("categories"):
        payload["categories"] = raw_payload.get("categories") or []

    if action == "show_products" or raw_payload.get("products"):
        payload["products"] = raw_payload.get("products") or []
        if raw_payload.get("search_query") is not None:
            payload["search_query"] = raw_payload.get("search_query")
        for key in ("category", "subcategory", "category_label"):
            if raw_payload.get(key) is not None:
                payload[key] = raw_payload.get(key)

    if action in {"show_checkout", "update_cart"}:
        checkout_result = result.get("checkout_result") or {}
        for key in ("checkout_url", "order_ref", "summary", "expires_at"):
            if checkout_result.get(key) is not None:
                payload[key] = checkout_result[key]

    return payload
