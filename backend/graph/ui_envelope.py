"""Enrich UI JSON payloads with full session context for the frontend."""

from __future__ import annotations

from typing import Any


def enrich_ui_payload(result: dict[str, Any]) -> dict[str, Any]:
    """Merge cart, delivery, and checkout context into every UI envelope."""
    ui_action = result.get("ui_action") or {}
    payload = dict(ui_action.get("payload") or {})
    payload["cart"] = result.get("cart") or []
    payload["delivery_info"] = result.get("delivery_info") or {}
    payload["checkout_info"] = result.get("checkout_info") or {}
    return payload
