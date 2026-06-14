"""Category-scoped Kapruka product search with keyword fallbacks."""

from __future__ import annotations

import logging
from typing import Any

from graph.category_catalog import FEATURED_CATALOG, catalog_label
from kapruka_mcp.kapruka_tools import KaprukaMCPError, kapruka_search_products

logger = logging.getLogger(__name__)


def _catalog_entry(parent: str, *, label: str | None = None) -> dict[str, Any] | None:
    if label:
        for entry in FEATURED_CATALOG:
            if entry["mcp_name"] == parent and entry["label"] == label:
                return entry
    return next((entry for entry in FEATURED_CATALOG if entry["mcp_name"] == parent), None)


def _default_query(parent: str, *, subcategory: str | None, label: str | None) -> str:
    if subcategory:
        return subcategory
    entry = _catalog_entry(parent, label=label)
    if entry and entry.get("search_hint"):
        return str(entry["search_hint"])
    return catalog_label(parent, fallback=parent)


def _search(
    *,
    q: str,
    category: str | None,
    limit: int,
    in_stock_only: bool,
) -> list[dict[str, Any]]:
    result = kapruka_search_products(
        q=q,
        category=category,
        in_stock_only=in_stock_only,
        limit=limit,
    )
    return result.get("results") or []


def search_category_products(
    parent: str,
    *,
    subcategory: str | None = None,
    label: str | None = None,
    limit: int = 10,
    in_stock_only: bool = True,
) -> dict[str, Any]:
    """
    Search products for a Kapruka category browse selection.

    Fallback chain:
    1. category filter + subcategory/parent query
    2. keyword-only parent/hint query
    3. keyword-only subcategory query
    """
    parent = (parent or "").strip()
    subcategory = (subcategory or "").strip() or None
    label = (label or "").strip() or None
    query = _default_query(parent, subcategory=subcategory, label=label)
    search_query = query

    strategies: list[tuple[str, str, str | None]] = [
        ("category_filter", query, parent),
        ("keyword_parent", query, None),
    ]
    if subcategory and subcategory.lower() != query.lower():
        strategies.append(("keyword_subcategory", subcategory, None))

    last_error: KaprukaMCPError | None = None
    for strategy, q, category in strategies:
        try:
            products = _search(q=q, category=category, limit=limit, in_stock_only=in_stock_only)
        except KaprukaMCPError as exc:
            last_error = exc
            continue

        if products:
            logger.info(
                "Category search %s via %s (q=%r category=%r) -> %s products",
                parent,
                strategy,
                q,
                category,
                len(products),
            )
            return {
                "products": products,
                "strategy": strategy,
                "search_query": search_query,
                "category": parent,
                "subcategory": subcategory,
                "label": label or catalog_label(parent),
            }

    if last_error is not None:
        raise last_error

    return {
        "products": [],
        "strategy": "none",
        "search_query": search_query,
        "category": parent,
        "subcategory": subcategory,
        "label": label or catalog_label(parent),
    }
