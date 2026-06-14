"""Cached Kapruka category list for the frontend picker."""

from __future__ import annotations

import time
from typing import Any

from graph.category_catalog import enrich_categories_tree
from kapruka_mcp.kapruka_tools import KaprukaMCPError, kapruka_list_categories

CACHE_TTL_SECONDS = 30 * 60

_cache: dict[tuple[int, bool], tuple[float, dict[str, Any]]] = {}


def get_categories(*, depth: int = 2, featured_only: bool = False) -> dict[str, Any]:
    """Return Kapruka categories enriched with display metadata."""
    depth = 2 if depth >= 2 else 1
    cache_key = (depth, featured_only)
    now = time.monotonic()
    cached = _cache.get(cache_key)
    if cached and now - cached[0] < CACHE_TTL_SECONDS:
        return cached[1]

    try:
        raw = kapruka_list_categories(depth=depth)
    except KaprukaMCPError as exc:
        raise exc

    mcp_categories = raw.get("categories") or []
    categories = enrich_categories_tree(mcp_categories, featured_only=featured_only)
    payload = {
        "categories": categories,
        "depth": depth,
        "featured_only": featured_only,
        "count": len(categories),
    }
    _cache[cache_key] = (now, payload)
    return payload


def clear_categories_cache() -> None:
    _cache.clear()
