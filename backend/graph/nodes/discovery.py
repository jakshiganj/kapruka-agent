from __future__ import annotations

import re
from typing import Any

from graph.category_catalog import catalog_label
from graph.category_search import search_category_products
from graph.state import AgentState
from graph.voice_i18n import voice_msg
from graph.product_pick import (
    pick_product_from_text,
    resolve_search_query,
    strip_intent_lead_in,
    wants_add_product,
)
from kapruka_mcp.kapruka_tools import KaprukaMCPError, kapruka_search_products


# Map common free-text gift terms to a Kapruka category so we scope the search
# (raw keyword search returned junk like a thesaurus for "chocolate" or
# "Machan Computers" for Tanglish). Keys are matched as whole words.
_CATEGORY_KEYWORDS: dict[str, str] = {
    "cake": "cakes", "cakes": "cakes", "gateau": "cakes",
    "chocolate": "Chocolates", "chocolates": "Chocolates", "choc": "Chocolates",
    "flower": "flowers", "flowers": "flowers", "bouquet": "flowers", "roses": "flowers",
    "perfume": "Perfumes", "perfumes": "Perfumes", "fragrance": "Perfumes", "cologne": "Perfumes",
    "hamper": "combopack", "hampers": "combopack",
    "fruit": "Fruits", "fruits": "Fruits",
    "vegetable": "Vegetables", "vegetables": "Vegetables", "veg": "Vegetables",
    "jewelry": "Jewellery", "jewellery": "Jewellery", "watch": "Jewellery",
    "ring": "Jewellery", "necklace": "Jewellery", "bracelet": "Jewellery",
    "toy": "KidsToys", "toys": "KidsToys",
    "book": "Books", "books": "Books",
    "cosmetic": "Cosmetics", "cosmetics": "Cosmetics", "makeup": "Cosmetics",
    "baby": "BabyItems",
    "grocery": "Grocery", "groceries": "Grocery",
    "cushion": "Personalized Gifts", "mug": "Personalized Gifts", "frame": "Personalized Gifts",
}


def _infer_category(query: str) -> str | None:
    # Prefer the last matching token — the head noun in English usually comes
    # last ("chocolate cake" -> cakes, "fruit basket" -> Fruits).
    tokens = re.findall(r"[a-z]+", query.lower())
    inferred: str | None = None
    for token in tokens:
        category = _CATEGORY_KEYWORDS.get(token)
        if category:
            inferred = category
    return inferred


def _filter_relevant(products: list[dict[str, Any]], query: str) -> list[dict[str, Any]]:
    """Drop results with zero query-token overlap, but only if enough remain."""
    tokens = [t for t in re.findall(r"[a-z0-9]+", query.lower()) if len(t) > 2]
    if not tokens:
        return products
    relevant = [
        p
        for p in products
        if any(
            t in f"{p.get('name', '')} {p.get('summary', '') or ''}".lower()
            for t in tokens
        )
    ]
    return relevant if len(relevant) >= 3 else products


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
        return strip_intent_lead_in(resolved)

    ui_payload = (state.get("ui_action") or {}).get("payload") or {}
    if ui_payload.get("search_query"):
        return str(ui_payload["search_query"])

    # No clean query extracted — trim the voice model's conversational framing
    # ("user wants to look for chocolates" -> "chocolates") before searching.
    cleaned = strip_intent_lead_in(user_text)
    return cleaned or "chocolate cake"


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
            # Scope known gift terms to their category for far better relevance;
            # fall back to a plain keyword search otherwise.
            inferred = _infer_category(query)
            if inferred:
                browse = search_category_products(inferred, limit=10)
                products = browse.get("products") or []
                if not products:
                    result = kapruka_search_products(q=query, in_stock_only=True, limit=10)
                    products = _filter_relevant(result.get("results") or [], query)
            else:
                result = kapruka_search_products(q=query, in_stock_only=True, limit=10)
                products = _filter_relevant(result.get("results") or [], query)
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
                f"I couldn't find any in-stock matches for {empty_label}. "
                "Try a different term, or tap a category below to browse — "
                "cakes, flowers, chocolates, hampers, perfumes."
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
        voice_prompt = voice_msg(
            "products_found",
            state,
            count=len(products),
            query=query,
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
