from __future__ import annotations

from typing import Any

from graph.state import AgentState
from kapruka_mcp.kapruka_tools import kapruka_search_products


def _search_query(state: AgentState) -> str:
    ui_payload = (state.get("ui_action") or {}).get("payload") or {}
    if ui_payload.get("search_query"):
        return ui_payload["search_query"]

    for message in reversed(state["messages"]):
        content = str(getattr(message, "content", ""))
        if content:
            return content
    return "chocolate cake"


def discovery_node(state: AgentState) -> dict[str, Any]:
    query = _search_query(state)
    result = kapruka_search_products(q=query, in_stock_only=True, limit=10)
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

    selected = next(
        (product for product in products if product.get("in_stock")),
        products[0],
    )

    return {
        "ui_action": {
            "action": "show_products",
            "payload": {
                "products": products,
                "selected_product": selected,
                "search_query": query,
            },
        },
        "voice_prompt": (
            f"I found {len(products)} options for '{query}'. "
            f"The top match is {selected.get('name')}."
        ),
        "next_node": "cart_manager",
    }
