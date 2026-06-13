import asyncio
import json

from langchain_core.messages import HumanMessage

from graph.graph import build_graph
from live.connection_pool import create_session

INTENT = "I want to send a chocolate cake to Kadawatha on 2026-06-25"


async def main() -> None:
    app = build_graph()
    session = create_session()

    initial_state = {
        "messages": [HumanMessage(content=INTENT)],
        "cart": [],
        "delivery_info": {},
        "checkout_info": {},
        "ui_action": {},
        "voice_prompt": "",
        "next_node": "discovery",
    }

    result = await app.ainvoke(
        initial_state,
        config={"configurable": {"thread_id": session["langgraph_thread_id"]}},
    )

    session["agent_state"] = result

    print(
        json.dumps(
            {
                "ui_action": result["ui_action"],
                "cart": result["cart"],
                "delivery_info": result["delivery_info"],
                "voice_prompt": result["voice_prompt"],
            },
            indent=2,
            default=str,
        )
    )

    assert result["ui_action"]["payload"].get("products") or result["ui_action"]["payload"].get("cart"), (
        "Expected real MCP products or cart payload"
    )
    assert len(result["cart"]) >= 1
    assert result["cart"][0]["product_id"]
    assert result["cart"][0]["price"] > 0
    assert "Kadawatha" in result["delivery_info"]["city"]
    assert result["delivery_info"]["date"] == "2026-06-25"
    assert result["voice_prompt"], "Expected delivery validation voice prompt"
    print("\nPhase 2 gate passed: graph returned real MCP data end-to-end.")


if __name__ == "__main__":
    asyncio.run(main())
