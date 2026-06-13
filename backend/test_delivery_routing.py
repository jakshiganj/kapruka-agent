"""Regression tests for delivery city/date routing."""

from __future__ import annotations

import asyncio

from langchain_core.messages import HumanMessage

from graph.graph import build_graph
from graph.nodes.router import _extract_delivery_from_text, router_node
from graph.product_pick import resolve_search_query
from live.connection_pool import create_session


def test_extract_delivery_phrases() -> None:
    cases = {
        "Kadawatha on 2026-06-25": {"city": "Kadawatha", "date": "2026-06-25"},
        "Delivery to Kadawatha on 2026-06-25": {"city": "Kadawatha", "date": "2026-06-25"},
        "Deliver to Kadawatha on 2026-06-25": {"city": "Kadawatha", "date": "2026-06-25"},
    }
    for text, expected in cases.items():
        got = _extract_delivery_from_text(text)
        assert got.get("city") == expected["city"], (text, got)
        assert got.get("date") == expected["date"], (text, got)


async def test_delivery_after_cart() -> None:
    app = build_graph()
    session = create_session()
    cfg = {
        "configurable": {"thread_id": session["langgraph_thread_id"]},
        "recursion_limit": 12,
    }

    async def invoke(intent: str, state: dict) -> dict:
        return await app.ainvoke(
            {
                **state,
                "messages": state["messages"] + [HumanMessage(content=intent)],
                "voice_mode": True,
            },
            config=cfg,
        )

    state = {
        "messages": [],
        "cart": [],
        "delivery_info": {},
        "checkout_info": {},
        "ui_action": {},
        "voice_prompt": "",
        "next_node": "discovery",
    }
    state = await invoke("I want a chocolate cake", state)
    selected = state["ui_action"]["payload"]["products"][0]
    ui_action = dict(state["ui_action"])
    ui_action["payload"] = {**ui_action["payload"], "selected_product": selected}
    state = await invoke(f"Add {selected['name']} to cart", {**state, "ui_action": ui_action})
    state = await invoke("I want flowers", state)

    for phrase in (
        "Kadawatha on 2026-06-25",
        "Delivery to Kadawatha on 2026-06-25",
        "I want delivery to Kadawatha on 2026-06-25",
    ):
        probe = router_node(
            {
                **state,
                "messages": state["messages"] + [HumanMessage(content=phrase)],
            }
        )
        assert probe.get("next_node") == "validation", (phrase, probe.get("next_node"))
        assert resolve_search_query(
            phrase,
            products=state["ui_action"]["payload"]["products"],
            cart=state["cart"],
        ) is None, phrase

        trial = await invoke(phrase, state)
        info = trial.get("delivery_info") or {}
        assert info.get("validated") == "true", (phrase, info, trial.get("voice_prompt"))


if __name__ == "__main__":
    test_extract_delivery_phrases()
    asyncio.run(test_delivery_after_cart())
    print("Delivery routing tests passed.")
