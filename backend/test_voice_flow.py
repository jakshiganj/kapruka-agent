"""Simulate the voice order flow: search → pick → delivery → checkout."""

import asyncio
import json

from langchain_core.messages import HumanMessage

from graph.graph import build_graph
from kapruka_mcp.kapruka_tools import get_mcp_stats, reset_mcp_stats
from live.connection_pool import create_session


async def main() -> None:
    reset_mcp_stats()
    app = build_graph()
    session = create_session()

    async def invoke(intent: str, state: dict) -> dict:
        result = await app.ainvoke(
            {
                **state,
                "messages": state["messages"] + [HumanMessage(content=intent)],
                "voice_mode": True,
            },
            config={"configurable": {"thread_id": session["langgraph_thread_id"]}},
        )
        return result

    state = {
        "messages": [],
        "cart": [],
        "delivery_info": {},
        "checkout_info": {},
        "ui_action": {},
        "voice_prompt": "",
        "next_node": "discovery",
    }

    # Turn 1 — search only; user must pick before cart is filled
    state = await invoke("I want a chocolate cake", state)
    assert state["ui_action"].get("action") == "show_products"
    assert not state["cart"], "Cart should stay empty until user picks a product"

    # Turn 2 — explicit product choice
    state = await invoke("Add the first chocolate cake", state)
    assert state["cart"], "Expected cart after product selection"
    assert state["delivery_info"].get("validated") != "true"

    # Turn 2b — second product search while cart has an item
    state = await invoke("I want flowers", state)
    assert state["ui_action"].get("action") == "show_products", state
    assert "flower" in str(state["ui_action"]["payload"].get("search_query", "")).lower()
    assert len(state["cart"]) == 1, "Original cart item should remain during new search"

    # Turn 3 — city + date
    state = await invoke("Kadawatha on 2026-06-25", state)
    assert state["cart"], "Expected cart after city/date turn"
    assert state["delivery_info"].get("validated") == "true", state.get("voice_prompt")

    # Turn 4 — checkout details
    state = await invoke(
        "Checkout. Recipient Amara Silva, phone 0771234567, "
        "address 123 Main Street Kadawatha, sender Jakshigan.",
        state,
    )
    assert state["ui_action"]["action"] == "show_checkout", state
    assert state["ui_action"]["payload"].get("checkout_url"), state

    stats = get_mcp_stats()
    print(json.dumps({"voice_prompt": state.get("voice_prompt"), "stats": stats}, indent=2, default=str))
    assert stats["by_tool"].get("kapruka_search_products", 0) >= 2, stats
    assert "kapruka_check_delivery" in stats["by_tool"], stats
    assert "kapruka_create_order" in stats["by_tool"], stats
    print("\nVoice flow passed (including second search).")


if __name__ == "__main__":
    asyncio.run(main())
