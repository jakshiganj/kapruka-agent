"""Order phase and checkout snapshot helpers for post-link cart edits."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Literal

from graph.state import AgentState

OrderPhase = Literal["shopping", "link_ready", "branch_pending"]

ADD_TO_ORDER_PATTERN = (
    r"\b(add to (?:this |the )?order|same order|this order|extend (?:the )?order|"
    r"keep (?:the )?cart|add (?:it )?to (?:my )?cart|yes add)\b"
)
NEW_GIFT_PATTERN = (
    r"\b(new gift|new order|start (?:a )?new|fresh (?:order|gift)|"
    r"different (?:gift|order)|separate (?:gift|order)|clear cart|"
    r"start over|begin again)\b"
)


def normalize_cart_line(item: dict[str, Any]) -> tuple[str, int]:
    product_id = str(item.get("product_id") or item.get("id") or "")
    quantity = int(item.get("quantity") or 1)
    return product_id, quantity


def cart_snapshot(cart: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Deep copy of cart lines for snapshot storage."""
    return deepcopy(cart)


def cart_matches_snapshot(cart: list[dict[str, Any]], snapshot: list[dict[str, Any]]) -> bool:
    if not snapshot:
        return not cart
    live = sorted(normalize_cart_line(item) for item in cart)
    frozen = sorted(normalize_cart_line(item) for item in snapshot)
    return live == frozen


def checkout_link_ready(state: AgentState) -> bool:
    return bool((state.get("checkout_result") or {}).get("checkout_url"))


def is_checkout_stale(state: AgentState) -> bool:
    snapshot = state.get("checkout_cart_snapshot") or []
    if not snapshot:
        return False
    cart = state.get("cart") or []
    return not cart_matches_snapshot(cart, snapshot)


def parse_branch_choice(user_text: str) -> Literal["add_to_order", "new_gift"] | None:
    import re

    text = user_text.strip()
    if not text:
        return None
    if re.search(NEW_GIFT_PATTERN, text, re.IGNORECASE):
        return "new_gift"
    if re.search(ADD_TO_ORDER_PATTERN, text, re.IGNORECASE):
        return "add_to_order"
    return None


def invalidate_checkout(state: AgentState) -> dict[str, Any]:
    """Clear active checkout link; keep snapshot so UI can show stale warning."""
    return {
        "checkout_result": {},
        "order_phase": "shopping",
    }


def reset_order_session() -> dict[str, Any]:
    """Start a fresh gift flow — clears cart and all order context."""
    return {
        "cart": [],
        "delivery_info": {},
        "checkout_info": {},
        "checkout_result": {},
        "checkout_cart_snapshot": [],
        "order_phase": "shopping",
        "ui_action": {},
    }


def mark_link_ready(cart: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "checkout_cart_snapshot": cart_snapshot(cart),
        "order_phase": "link_ready",
    }


def branch_prompt() -> str:
    return (
        "You already have a payment link open. Should I add this to that order, "
        "or start a new gift? Say 'add to this order' or 'new gift'."
    )
