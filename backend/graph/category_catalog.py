"""Curated Kapruka category display catalog — mirrors kapruka.com gift grid (~39 items)."""

from __future__ import annotations

import re
from typing import Any

CategoryEntry = dict[str, Any]

# Gift-relevant categories from the Kapruka.com reference grid (39 entries).
FEATURED_CATALOG: list[CategoryEntry] = [
    {"mcp_name": "cakes", "label": "Cake Shop", "icon_slug": "cakes", "sort_order": 1},
    {"mcp_name": "combopack", "label": "Combo Gift Packs", "icon_slug": "combopack", "sort_order": 2},
    {"mcp_name": "Chocolates", "label": "Chocolates", "icon_slug": "chocolates", "sort_order": 3},
    {"mcp_name": "Clothing", "label": "Clothing", "icon_slug": "clothing", "sort_order": 4},
    {"mcp_name": "Electronic", "label": "Electronics", "icon_slug": "electronics", "sort_order": 5},
    {"mcp_name": "flowers", "label": "Flower Shop", "icon_slug": "flowers", "sort_order": 6},
    {"mcp_name": "Food", "label": "Food & Restaurants", "icon_slug": "food", "sort_order": 7},
    {"mcp_name": "Fruits", "label": "Fruit & Fruit Baskets", "icon_slug": "fruits", "sort_order": 8},
    {"mcp_name": "Vegetables", "label": "Veg & Veg Baskets", "icon_slug": "vegetables", "sort_order": 9},
    {"mcp_name": "Giftcert", "label": "Gift Vouchers & Tickets", "icon_slug": "giftcert", "sort_order": 10},
    {"mcp_name": "Giftset", "label": "Combo and Gift Sets", "icon_slug": "giftset", "sort_order": 11},
    {"mcp_name": "Grocery", "label": "Grocery Items", "icon_slug": "grocery", "sort_order": 12},
    {"mcp_name": "GreetingCards", "label": "Greeting Cards & Party", "icon_slug": "greeting_cards", "sort_order": 13},
    {
        "mcp_name": "combopack",
        "label": "Hampers",
        "icon_slug": "hampers",
        "sort_order": 14,
        "search_hint": "hampers",
    },
    {"mcp_name": "Jewellery", "label": "Jewelry & Watches", "icon_slug": "jewellery", "sort_order": 15},
    {
        "mcp_name": "Personalized Gifts",
        "label": "Personalized Gifts",
        "icon_slug": "personalized_gifts",
        "sort_order": 16,
    },
    {"mcp_name": "Perfumes", "label": "Perfumes & Fragrances", "icon_slug": "perfumes", "sort_order": 17},
    {"mcp_name": "Fashion", "label": "Hand Bags & Fashion & Shoes", "icon_slug": "fashion", "sort_order": 18},
    {"mcp_name": "Cosmetics", "label": "Cosmetics", "icon_slug": "cosmetics", "sort_order": 19},
    {"mcp_name": "Schoolpride", "label": "College Pride", "icon_slug": "schoolpride", "sort_order": 20},
    {"mcp_name": "Childrens", "label": "School Supplies", "icon_slug": "school_supplies", "sort_order": 21},
    {"mcp_name": "Books", "label": "Books", "icon_slug": "books", "sort_order": 22},
    {"mcp_name": "Pharmacy", "label": "Health and Wellness", "icon_slug": "pharmacy", "sort_order": 23},
    {"mcp_name": "KidsToys", "label": "Soft Toys & Kids Toys", "icon_slug": "kids_toys", "sort_order": 24},
    {"mcp_name": "Bicycle", "label": "Sports & Bicycles", "icon_slug": "sports", "sort_order": 25},
    {"mcp_name": "BabyItems", "label": "Mother & Baby", "icon_slug": "baby", "sort_order": 26},
    {"mcp_name": "Household", "label": "Home & Lifestyle", "icon_slug": "household", "sort_order": 27},
    {"mcp_name": "pirikara", "label": "Religious Items", "icon_slug": "pirikara", "sort_order": 28},
    {"mcp_name": "Automobile", "label": "Automobile", "icon_slug": "automobile", "sort_order": 29},
    {"mcp_name": "Pet", "label": "Petcare", "icon_slug": "pet", "sort_order": 30},
    {"mcp_name": "Adult Products", "label": "Intimate Essentials", "icon_slug": "adult", "sort_order": 31},
    {"mcp_name": "uniquegifts", "label": "Made in SL", "icon_slug": "made_in_sl", "sort_order": 32},
    {
        "mcp_name": "promotions",
        "label": "Kapruka Global Shop",
        "icon_slug": "global_shop",
        "sort_order": 33,
        "search_hint": "global shop",
    },
    {
        "mcp_name": "samedaydelivery",
        "label": "Gifts to Other Countries",
        "icon_slug": "international",
        "sort_order": 34,
        "search_hint": "international gifts",
    },
    {
        "mcp_name": "Schoolpride",
        "label": "Get SL Merchandise",
        "icon_slug": "merchandise",
        "sort_order": 35,
        "search_hint": "merchandise",
    },
    {"mcp_name": "Services", "label": "Services", "icon_slug": "services", "sort_order": 36},
    {
        "mcp_name": "Giftcert",
        "label": "Reload Mobile Phones",
        "icon_slug": "mobile_reload",
        "sort_order": 37,
        "search_hint": "mobile reload",
    },
    {
        "mcp_name": "Giftcert",
        "label": "Send Money & Vouchers",
        "icon_slug": "money_vouchers",
        "sort_order": 38,
        "search_hint": "gift voucher money",
    },
    {
        "mcp_name": "Services",
        "label": "Realestate Services",
        "icon_slug": "realestate",
        "sort_order": 39,
        "search_hint": "real estate",
    },
]

ICON_EMOJI: dict[str, str] = {
    "cakes": "🎂",
    "combopack": "🧸",
    "chocolates": "🍫",
    "clothing": "👕",
    "electronics": "📻",
    "flowers": "💐",
    "food": "🍔",
    "fruits": "🍎",
    "vegetables": "🥦",
    "giftcert": "🎫",
    "giftset": "🎁",
    "grocery": "🛒",
    "greeting_cards": "✉️",
    "hampers": "🧺",
    "jewellery": "⌚",
    "personalized_gifts": "☕",
    "perfumes": "🧴",
    "fashion": "👜",
    "cosmetics": "💄",
    "schoolpride": "🎓",
    "school_supplies": "✏️",
    "books": "📚",
    "pharmacy": "🏥",
    "kids_toys": "🧸",
    "sports": "🚲",
    "baby": "👶",
    "household": "🏠",
    "pirikara": "🛐",
    "automobile": "🏍️",
    "pet": "🐾",
    "adult": "🔞",
    "made_in_sl": "🇱🇰",
    "global_shop": "🌐",
    "international": "✈️",
    "merchandise": "👕",
    "services": "🛠️",
    "mobile_reload": "📱",
    "money_vouchers": "💸",
    "realestate": "🏘️",
}

_CATALOG_BY_MCP: dict[str, CategoryEntry] = {
    entry["mcp_name"]: entry for entry in FEATURED_CATALOG
}


def _humanize_name(name: str) -> str:
    cleaned = re.sub(r"[_\-]+", " ", name.strip())
    return cleaned[:1].upper() + cleaned[1:] if cleaned else name


def icon_url(icon_slug: str) -> str:
    return f"/categories/{icon_slug}.webp"


def catalog_entry_for(mcp_name: str) -> CategoryEntry | None:
    return _CATALOG_BY_MCP.get(mcp_name)


def catalog_label(mcp_name: str, *, fallback: str | None = None) -> str:
    entry = catalog_entry_for(mcp_name)
    if entry:
        return str(entry["label"])
    return fallback or _humanize_name(mcp_name)


def _enrich_node(node: dict[str, Any], *, catalog: CategoryEntry | None = None) -> dict[str, Any]:
    name = str(node.get("name") or "")
    entry = catalog or catalog_entry_for(name)
    label = str(entry["label"]) if entry else _humanize_name(name)
    icon_slug = str(entry["icon_slug"]) if entry else re.sub(r"\s+", "_", name.lower())
    emoji = ICON_EMOJI.get(icon_slug, "🎁")

    enriched: dict[str, Any] = {
        **node,
        "name": name,
        "label": label,
        "icon_slug": icon_slug,
        "iconUrl": icon_url(icon_slug),
        "emoji": emoji,
        "featured": entry is not None,
    }
    if entry and entry.get("search_hint"):
        enriched["search_hint"] = entry["search_hint"]

    children = node.get("children") or []
    if children:
        enriched["children"] = [
            {
                **child,
                "name": child.get("name"),
                "label": _humanize_name(str(child.get("name") or "")),
            }
            for child in children
        ]
    return enriched


def _merge_featured_with_mcp(
    mcp_categories: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_name = {str(item.get("name") or ""): item for item in mcp_categories}
    merged: list[dict[str, Any]] = []
    for entry in sorted(FEATURED_CATALOG, key=lambda item: int(item["sort_order"])):
        mcp_node = by_name.get(entry["mcp_name"], {"name": entry["mcp_name"]})
        merged.append(_enrich_node(mcp_node, catalog=entry))
    return merged


def enrich_categories_tree(
    mcp_categories: list[dict[str, Any]],
    *,
    featured_only: bool = False,
) -> list[dict[str, Any]]:
    """Merge MCP category tree with display labels, emoji, and icon URLs."""
    if featured_only:
        return _merge_featured_with_mcp(mcp_categories)

    enriched = [_enrich_node(node) for node in mcp_categories]
    enriched.sort(
        key=lambda node: (
            not node.get("featured"),
            _CATALOG_BY_MCP.get(str(node.get("name") or ""), {}).get("sort_order", 999),
            str(node.get("label") or node.get("name") or ""),
        )
    )
    return enriched
