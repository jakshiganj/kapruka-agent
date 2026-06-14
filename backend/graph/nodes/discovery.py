from __future__ import annotations

from typing import Any

from graph.category_catalog import catalog_label
from graph.category_search import search_category_products
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


def _browse_context(state: AgentState) -> tuple[str | None, str | None, str | None]:
    ui_payload = (state.get("ui_action") or {}).get("payload") or {}
    category = ui_payload.get("category")
    subcategory = ui_payload.get("subcategory")
    label = ui_payload.get("category_label") or ui_payload.get("label")
    if category:
        return str(category), str(subcategory) if subcategory else None, str(label) if label else None
    return None, None, None


def discovery_node(state: AgentState) -> dict[str, Any]:
    category, subcategory, label = _browse_context(state)
    query = _search_query(state)

    try:
        if category:
            browse = search_category_products(
                category,
                subcategory=subcategory,
                label=label,
                limit=10,
            )
            products = browse.get("products") or []
            query = str(browse.get("search_query") or query)
            browse_label = str(browse.get("label") or catalog_label(category))
        else:
            result = kapruka_search_products(q=query, in_stock_only=True, limit=10)
            products = result.get("results") or []
            browse_label = None
    except KaprukaMCPError as exc:
        message = str(exc).removeprefix("Error:").strip()
        error_payload: dict[str, Any] = {"products": [], "search_query": query, "error": message}
        if category:
            error_payload["category"] = category
            if subcategory:
                error_payload["subcategory"] = subcategory
        return {
            "ui_action": {
                "action": "show_products",
                "payload": error_payload,
            },
            "voice_prompt": (
                "Kapruka's product search is busy right now. "
                f"{message} Please wait a few seconds and try again."
            ),
            "next_node": "end",
        }

    if not products:
        empty_payload: dict[str, Any] = {"products": [], "search_query": query}
        if category:
            empty_payload["category"] = category
            if subcategory:
                empty_payload["subcategory"] = subcategory
        empty_label = subcategory or browse_label or category or query
        return {
            "ui_action": {
                "action": "show_products",
                "payload": empty_payload,
            },
            "voice_prompt": (
                f"I couldn't find any in-stock products in {empty_label}. "
                "Try another subcategory or tell me what you'd like to send."
            ),
            "next_node": "end",
        }

    user_text = _latest_user_text(state)
    selected = pick_product_from_text(user_text, products) if wants_add_product(user_text) else None

    if category:
        display = subcategory or browse_label or catalog_label(category)
        voice_prompt = (
            f"Here are {len(products)} Kapruka picks from {display} — they're on your screen now. "
            "Tap the one you like, or tell me which to add."
        )
    else:
        voice_prompt = (
            f"I found {len(products)} Kapruka options for '{query}' — they're on your screen now. "
            "Tap the one you like, or tell me which to add — for example, the second cake or Lavender Love."
        )

    payload: dict[str, Any] = {
        "products": products,
        "search_query": query,
    }
    if category:
        payload["category"] = category
        if subcategory:
            payload["subcategory"] = subcategory
        if browse_label:
            payload["category_label"] = browse_label
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
