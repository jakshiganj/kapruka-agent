"""Gate test: validated cart -> checkout with payment link."""

import asyncio
import json

from langchain_core.messages import HumanMessage

from graph.graph import build_graph
from live.connection_pool import create_session


async def main() -> None:
    app = build_graph()
    session = create_session()

    # Turn 1 — search + validate (same as test_graph)
    state = {
        "messages": [HumanMessage(content="I want to send a chocolate cake to Kadawatha on 2026-06-25")],
        "cart": [],
        "delivery_info": {},
        "checkout_info": {},
        "ui_action": {},
        "voice_prompt": "",
        "next_node": "discovery",
    }
    result = await app.ainvoke(
        state,
        config={"configurable": {"thread_id": session["langgraph_thread_id"]}},
    )
    assert result["delivery_info"].get("validated") == "true"
    assert result["cart"]

    # Turn 2 — checkout details
    checkout_intent = (
        "Please checkout. Recipient is Amara Silva, phone 0771234567, "
        "address 123 Main Street Kadawatha, sender is Jakshigan."
    )
    result = await app.ainvoke(
        {
            **result,
            "messages": result["messages"] + [HumanMessage(content=checkout_intent)],
            "voice_mode": True,
        },
        config={"configurable": {"thread_id": session["langgraph_thread_id"]}},
    )

    print(json.dumps({
        "ui_action": result.get("ui_action"),
        "voice_prompt": result.get("voice_prompt"),
        "checkout_info": result.get("checkout_info"),
    }, indent=2, default=str))

    assert result["ui_action"]["action"] == "show_checkout", result
    assert result["ui_action"]["payload"].get("checkout_url"), "Expected payment URL"
    print("\nCheckout gate passed.")


if __name__ == "__main__":
    asyncio.run(main())
