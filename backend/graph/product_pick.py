"""Match user speech to visible Kapruka catalog products."""

from __future__ import annotations

import re
from typing import Any


ORDINALS: dict[str, int] = {
    "first": 0,
    "1st": 0,
    "one": 0,
    "second": 1,
    "2nd": 1,
    "two": 1,
    "third": 2,
    "3rd": 2,
    "three": 2,
    "fourth": 3,
    "4th": 3,
    "fifth": 4,
    "5th": 4,
}

ISO_DATE_PATTERN = re.compile(r"\b(20\d{2}-\d{2}-\d{2})\b")

ADD_PRODUCT_PATTERN = re.compile(
    r"\b("
    r"add|adding|also add|add another|add the|put|include|take|choose|pick|select|"
    r"want the|want that|get the|get that|order the|send the|"
    r"this one|that one|the one|from the list|from the screen|"
    r"second one|third one|first one|top one|bottom one"
    r")\b",
    re.IGNORECASE,
)

NEW_SEARCH_PATTERN = re.compile(
    r"(?:also add|add another|add|search(?:\s+for)?|find|get|show)\s+"
    r"(?:a|an|some|me)?\s*(.+?)(?:\s+to cart|\s+as well|\s+please|$)",
    re.IGNORECASE,
)


def wants_add_product(user_text: str) -> bool:
    return bool(ADD_PRODUCT_PATTERN.search(user_text))


def is_delivery_followup(user_text: str, *, cart: list[Any] | None = None) -> bool:
    """True when the user is giving delivery city/date rather than browsing products."""
    if not ISO_DATE_PATTERN.search(user_text):
        return False
    if cart:
        return True
    if re.search(
        r"(?i)\b(?:i want|i(?:'d| would) like|looking for|search(?:ing)? for|find|show me)\b",
        user_text,
    ) and re.search(r"(?i)\s+to\s+.+\s+on\s+20\d{2}-\d{2}-\d{2}\b", user_text):
        return False
    return True


def extract_followup_search_query(user_text: str) -> str | None:
    if re.search(
        r"(?i)\b(first|second|third|fourth|fifth|that one|this one|from the list|from the screen)\b",
        user_text,
    ):
        return None
    match = NEW_SEARCH_PATTERN.search(user_text.strip())
    if not match:
        return None
    query = match.group(1).strip(" .,!?:;")
    query = re.sub(
        r"(?i)\b(too|also|please|as well|to the cart|to cart|from the list)\b",
        "",
        query,
    ).strip()
    if len(query) >= 2 and not re.search(r"(?i)^(it|that|this|one|the)$", query):
        return query
    return None


def _name_tokens(name: str) -> list[str]:
    stop = {"cake", "for", "the", "and", "with", "love", "from", "kapruka"}
    return [t for t in re.findall(r"[a-z0-9]+", name.lower()) if len(t) > 2 and t not in stop]


def product_match_score(user_text: str, product: dict[str, Any]) -> int:
    text = user_text.lower()
    return sum(1 for token in _name_tokens(product.get("name", "")) if token in text)


CONFIRM_SELECTION_PATTERN = re.compile(
    r"\b(add|yes|confirm|go ahead|please|ok|okay|sure)\b",
    re.IGNORECASE,
)

BROWSE_SEARCH_PATTERN = re.compile(
    r"(?i)\b("
    r"i want(?: a| an| to)?|i(?:'d| would) like(?: a| an| to)?|"
    r"looking for|search(?:ing)? for|find (?:me )?|show me|can i get a|send a|send an"
    r")\b",
)


def extract_browse_search_query(user_text: str) -> str | None:
    """Extract a Kapruka catalog query from natural browse phrases."""
    text = user_text.strip().rstrip(".!?")
    text = re.sub(
        r"(?i)\s+to\s+.+?\s+on\s+20\d{2}-\d{2}-\d{2}\b",
        "",
        text,
    ).strip()

    patterns = (
        r"(?i)^(?:i want(?: a| an| to)?|i(?:'d| would) like(?: a| an| to)?|"
        r"looking for|search(?:ing)? for|find(?: me)?|show me|can i get a|send a|send an)\s+(.+)$",
        r"(?i)^(?:some|a|an)\s+(.+)$",
    )
    for pattern in patterns:
        match = re.match(pattern, text)
        if not match:
            continue
        query = match.group(1).strip(" .,!?:;")
        query = re.sub(
            r"(?i)\b(please|for delivery|for me|to cart|to my cart)\b",
            "",
            query,
        ).strip(" .,!?:;")
        if len(query) >= 2 and not re.search(r"(?i)^(it|that|this|one|the)$", query):
            return query
    return None


def _is_browse_search_intent(user_text: str) -> bool:
    if not BROWSE_SEARCH_PATTERN.search(user_text):
        return False
    if re.search(r"(?i)\b(add|first|second|third|fourth|fifth|that one|this one)\b", user_text):
        return False
    return True


def normalize_search_query(query: str | None) -> str:
    return re.sub(r"\s+", " ", (query or "").strip().lower())


def resolve_search_query(
    user_text: str,
    *,
    products: list[dict[str, Any]] | None = None,
    selected_product: dict[str, Any] | None = None,
    cart: list[Any] | None = None,
) -> str | None:
    """Best-effort Kapruka catalog query from the latest user utterance."""
    if is_delivery_followup(user_text, cart=cart):
        return None
    for extractor in (extract_browse_search_query, extract_followup_search_query):
        query = extractor(user_text)
        if query:
            if (
                products
                and not _is_browse_search_intent(user_text)
                and (
                    pick_product_from_text(user_text, products)
                    or resolve_carousel_pick(user_text, products, selected_product=selected_product)
                )
            ):
                return None
            return query.strip()
    if products and wants_add_product(user_text):
        if resolve_carousel_pick(user_text, products, selected_product=selected_product):
            return None
    return None


def resolve_carousel_pick(
    user_text: str,
    products: list[dict[str, Any]],
    *,
    selected_product: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    if not products:
        return None
    if selected_product and (
        wants_add_product(user_text) or CONFIRM_SELECTION_PATTERN.search(user_text)
    ):
        return selected_product
    if wants_add_product(user_text):
        return pick_product_from_text(user_text, products)
    if should_add_to_cart(user_text, products, selected_product=selected_product):
        return pick_product_from_text(user_text, products)
    return None


def route_cart_add_node(
    user_text: str,
    products: list[dict[str, Any]],
    cart: list[dict[str, Any]],
    *,
    selected_product: dict[str, Any] | None = None,
) -> str | None:
    """Return cart_manager once per pick; end when that product is already in the cart."""
    if not should_add_to_cart(user_text, products, selected_product=selected_product):
        return None
    picked = resolve_carousel_pick(user_text, products, selected_product=selected_product)
    if not picked:
        return None
    product_id = picked.get("id") or picked.get("product_id")
    if any(item["product_id"] == product_id for item in cart):
        return "end"
    return "cart_manager"


def should_add_to_cart(
    user_text: str,
    products: list[dict[str, Any]],
    *,
    selected_product: dict[str, Any] | None = None,
) -> bool:
    """True when the user explicitly chose a carousel product to add — never on search alone."""
    if not products:
        return False

    if _is_browse_search_intent(user_text) and not wants_add_product(user_text):
        return False

    if wants_add_product(user_text):
        return bool(pick_product_from_text(user_text, products) or selected_product)

    picked = pick_product_from_text(user_text, products)
    if picked and product_match_score(user_text, picked) >= 2:
        return True

    if selected_product and CONFIRM_SELECTION_PATTERN.search(user_text):
        return True

    return False


def pick_product_from_text(user_text: str, products: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not products:
        return None

    text = user_text.lower()

    for word, index in sorted(ORDINALS.items(), key=lambda item: -len(item[0])):
        if re.search(rf"\b{re.escape(word)}\b", text) and index < len(products):
            return products[index]

    best: dict[str, Any] | None = None
    best_score = 0
    for product in products:
        name = product.get("name", "")
        tokens = _name_tokens(name)
        if not tokens:
            continue
        score = sum(1 for token in tokens if token in text)
        if score > best_score:
            best_score = score
            best = product

    if best_score >= 2:
        return best
    if best_score >= 1 and best is not None and len(_name_tokens(best.get("name", ""))) <= 3:
        return best

    # Full name substring (user quoted a long product title)
    for product in products:
        name = product.get("name", "").lower()
        if len(name) >= 8 and name in text:
            return product

    return None
