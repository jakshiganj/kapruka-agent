"""Unit tests for query/date parsing helpers (no MCP or LLM)."""

from __future__ import annotations

from datetime import date

from graph.date_parse import extract_delivery_city_and_date, parse_natural_date
from graph.product_pick import (
    is_delivery_followup,
    resolve_followup_search_query,
    strip_intent_lead_in,
)


def test_strip_intent_lead_in() -> None:
    cases = {
        "user wants to look for chocolates": "chocolates",
        "Machan, chocolate cake ekak": "chocolate cake",
        "I want a chocolate cake please": "chocolate cake",
        "looking for vegetables": "vegetables",
        "chocolate cake": "chocolate cake",
    }
    for raw, expected in cases.items():
        assert strip_intent_lead_in(raw) == expected, raw


def test_parse_natural_date() -> None:
    today = date(2026, 6, 15)
    iso = parse_natural_date("kandy 30th", today=today, aggressive=True)
    assert iso is not None
    assert iso[0] == "2026-06-30"

    iso2 = parse_natural_date("2026-06-25", today=today, aggressive=False)
    assert iso2 is not None
    assert iso2[0] == "2026-06-25"

    assert parse_natural_date("30th birthday", today=today, aggressive=True) is None


def test_extract_delivery_city_and_date() -> None:
    today = date(2026, 6, 15)
    city, iso = extract_delivery_city_and_date("kandy, 30th", aggressive=True, today=today)
    assert city and city.lower().startswith("kandy"), city
    assert iso == "2026-06-30"

    city2, iso2 = extract_delivery_city_and_date(
        "Kadawatha on 2026-06-25", aggressive=False, today=today
    )
    assert city2 == "Kadawatha"
    assert iso2 == "2026-06-25"

    assert extract_delivery_city_and_date("the fifth option", aggressive=True) == (None, None)


def test_is_delivery_followup_natural_date() -> None:
    cart = [{"product_id": "CAKE1", "quantity": 1}]
    assert is_delivery_followup("kandy, 30th", cart=cart) is True
    assert is_delivery_followup("vegetables", cart=cart) is False
    assert is_delivery_followup("Kadawatha on 2026-06-25", cart=cart) is True


def test_resolve_followup_search_query() -> None:
    products = [{"id": "p1", "name": "Vegetable Duo Pack"}]

    assert (
        resolve_followup_search_query("search again for flowers", products) == "flowers"
    )
    assert resolve_followup_search_query("perfumes", products) == "perfumes"
    assert resolve_followup_search_query("kandy, 30th", products, cart=[{}]) is None
    assert (
        resolve_followup_search_query(
            "vegetables", products, allow_bare_noun=False, cart=[{}]
        )
        is None
    )


if __name__ == "__main__":
    test_strip_intent_lead_in()
    test_parse_natural_date()
    test_extract_delivery_city_and_date()
    test_is_delivery_followup_natural_date()
    test_resolve_followup_search_query()
    print("Product parse tests passed.")
