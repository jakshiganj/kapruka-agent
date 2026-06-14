"""Unit tests for post-checkout cart lifecycle."""

from graph.order_lifecycle import (
    cart_matches_snapshot,
    cart_snapshot,
    invalidate_checkout,
    is_checkout_stale,
    parse_branch_choice,
    reset_order_session,
)
from graph.nodes.router import _is_post_link_shopping_intent
from graph.ui_envelope import enrich_ui_payload


def test_cart_matches_snapshot():
    cart = [{"product_id": "cake001", "quantity": 1, "name": "Cake", "price": 1000}]
    snapshot = cart_snapshot(cart)
    assert cart_matches_snapshot(cart, snapshot)
    assert not cart_matches_snapshot(
        cart + [{"product_id": "flower001", "quantity": 1, "name": "Flowers", "price": 500}],
        snapshot,
    )


def test_parse_branch_choice():
    assert parse_branch_choice("Add to this order") == "add_to_order"
    assert parse_branch_choice("start a new gift") == "new_gift"
    assert parse_branch_choice("show me candy") is None


def test_invalidate_checkout_keeps_snapshot():
    state = {
        "checkout_result": {"checkout_url": "https://pay.example/1"},
        "checkout_cart_snapshot": [{"product_id": "cake001", "quantity": 1}],
        "order_phase": "link_ready",
        "cart": [{"product_id": "cake001", "quantity": 1}],
    }
    invalidated = invalidate_checkout(state)
    assert invalidated["checkout_result"] == {}
    assert invalidated["order_phase"] == "shopping"
    assert state["checkout_cart_snapshot"]


def test_is_checkout_stale_after_cart_change():
    state = {
        "checkout_result": {},
        "checkout_cart_snapshot": [{"product_id": "cake001", "quantity": 1}],
        "cart": [
            {"product_id": "cake001", "quantity": 1},
            {"product_id": "flower001", "quantity": 1},
        ],
    }
    assert is_checkout_stale(state)


def test_reset_order_session_clears_cart():
    reset = reset_order_session()
    assert reset["cart"] == []
    assert reset["checkout_result"] == {}
    assert reset["checkout_cart_snapshot"] == []
    assert reset["order_phase"] == "shopping"


def test_enrich_ui_payload_stale_flag():
    result = {
        "ui_action": {"action": "update_cart", "payload": {}},
        "cart": [
            {"product_id": "cake001", "quantity": 1},
            {"product_id": "flower001", "quantity": 1},
        ],
        "checkout_cart_snapshot": [{"product_id": "cake001", "quantity": 1}],
        "order_phase": "shopping",
    }
    payload = enrich_ui_payload(result)
    assert payload["checkout_stale"] is True
    assert payload["checkout_cart_snapshot"]["item_count"] == 1


def test_enrich_ui_payload_fresh_checkout_clears_stale():
    result = {
        "ui_action": {"action": "show_checkout", "payload": {}},
        "cart": [{"product_id": "cake001", "quantity": 1}],
        "checkout_cart_snapshot": [{"product_id": "cake001", "quantity": 1}],
        "checkout_result": {
            "checkout_url": "https://pay.example/2",
            "order_ref": "ORD-2",
        },
        "order_phase": "link_ready",
    }
    payload = enrich_ui_payload(result)
    assert payload.get("checkout_stale") is False
    assert payload["checkout_url"] == "https://pay.example/2"


def test_post_link_shopping_detects_new_search():
    state = {
        "checkout_result": {"checkout_url": "https://pay.example/1"},
        "cart": [{"product_id": "cake001", "quantity": 1}],
    }
    assert _is_post_link_shopping_intent(
        state,
        "any candy?",
        pending_query="candy",
        shown_query="cake",
        products=[],
        cart=state["cart"],
        payload={},
    )


def test_post_link_shopping_ignores_checkout_intent():
    state = {
        "checkout_result": {"checkout_url": "https://pay.example/1"},
        "cart": [{"product_id": "cake001", "quantity": 1}],
    }
    assert not _is_post_link_shopping_intent(
        state,
        "please checkout",
        pending_query="candy",
        shown_query="cake",
        products=[],
        cart=state["cart"],
        payload={},
    )


if __name__ == "__main__":
    test_cart_matches_snapshot()
    test_parse_branch_choice()
    test_invalidate_checkout_keeps_snapshot()
    test_is_checkout_stale_after_cart_change()
    test_reset_order_session_clears_cart()
    test_enrich_ui_payload_stale_flag()
    test_enrich_ui_payload_fresh_checkout_clears_stale()
    test_post_link_shopping_detects_new_search()
    test_post_link_shopping_ignores_checkout_intent()
    print("All post-checkout tests passed.")
