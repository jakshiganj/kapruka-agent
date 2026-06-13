import asyncio

from langchain_core.messages import HumanMessage

from graph.graph import build_graph
from live.connection_pool import create_session


async def main() -> None:
    app = build_graph()
    session = create_session()
    cfg = {
        "configurable": {"thread_id": session["langgraph_thread_id"]},
        "recursion_limit": 12,
    }

    state = {
        "messages": [HumanMessage(content="I want a chocolate cake")],
        "cart": [],
        "delivery_info": {},
        "checkout_info": {},
        "ui_action": {},
        "voice_prompt": "",
        "next_node": "discovery",
        "voice_mode": True,
    }
    state = await app.ainvoke(state, config=cfg)

    selected = state["ui_action"]["payload"]["products"][0]
    ui_action = dict(state["ui_action"])
    ui_action["payload"] = {**ui_action["payload"], "selected_product": selected}
    intent = f"Add {selected['name']} to cart"

    result = await app.ainvoke(
        {
            **state,
            "ui_action": ui_action,
            "messages": state["messages"] + [HumanMessage(content=intent)],
            "voice_mode": True,
        },
        config=cfg,
    )
    assert result["cart"], result
    assert result["ui_action"]["action"] == "update_cart", result
    print("Tap add OK:", result["cart"][0]["name"])

    # Stale selected_product from tap must not block a new search
    state_with_stale = {
        **result,
        "messages": result["messages"] + [HumanMessage(content="I want flowers")],
        "voice_mode": True,
    }
    flowers = await app.ainvoke(state_with_stale, config=cfg)
    assert flowers["ui_action"].get("action") == "show_products", flowers
    assert "flower" in str(flowers["ui_action"]["payload"].get("search_query", "")).lower()
    assert len(flowers["ui_action"]["payload"].get("products") or []) > 0
    print("Second search OK:", flowers["ui_action"]["payload"]["search_query"])


if __name__ == "__main__":
    asyncio.run(main())
