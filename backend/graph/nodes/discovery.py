from __future__ import annotations

from typing import Any

from graph.state import AgentState
from graph.product_pick import (
    pick_product_from_text,
    resolve_search_query,
    wants_add_product,
)
from kapruka_mcp.kapruka_tools import KaprukaMCPError, kapruka_search_products


def _latest_user_text(state: AgentState) -> str:
    from langchain_core.messages import HumanMessage

    for message in reversed(state["messages"]):
        if isinstance(message, HumanMessage):
            return str(message.content)
    return ""


def _search_query(state: AgentState) -> str:
    user_text = _latest_user_text(state)
    resolved = resolve_search_query(user_text)
    if resolved:
        return resolved

    ui_payload = (state.get("ui_action") or {}).get("payload") or {}
    if ui_payload.get("search_query"):
        return str(ui_payload["search_query"])

    return user_text.strip() or "chocolate cake"


def discovery_node(state: AgentState) -> dict[str, Any]:
    query = _search_query(state)
    try:
        result = kapruka_search_products(q=query, in_stock_only=True, limit=10)
    except KaprukaMCPError as exc:
        message = str(exc).removeprefix("Error:").strip()
        return {
            "ui_action": {
                "action": "show_products",
                "payload": {"products": [], "search_query": query, "error": message},
            },
            "voice_prompt": (
                "Kapruka's product search is busy right now. "
                f"{message} Please wait a few seconds and try again."
            ),
            "next_node": "end",
        }

    products = result.get("results") or []

    if not products:
        return {
            "ui_action": {
                "action": "show_products",
                "payload": {"products": [], "search_query": query},
            },
            "voice_prompt": f"I couldn't find any in-stock products for '{query}'. Could you try a different search?",
            "next_node": "end",
        }

    user_text = _latest_user_text(state)
    selected = pick_product_from_text(user_text, products) if wants_add_product(user_text) else None

    voice_prompt = (
        f"I found {len(products)} Kapruka options for '{query}' — they're on your screen now. "
        "Tap the one you like, or tell me which to add — for example, the second cake or Lavender Love."
    )

    payload: dict[str, Any] = {
        "products": products,
        "search_query": query,
    }
    if selected:
        payload["selected_product"] = selected

    return {
        "ui_action": {
            "action": "show_products",
            "payload": payload,
        },
        "voice_prompt": voice_prompt,
        "next_node": "end",
    }
