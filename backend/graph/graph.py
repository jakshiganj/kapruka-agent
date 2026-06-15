from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from graph.nodes.cart_manager import cart_manager_node
from graph.nodes.checkout import checkout_node
from graph.nodes.discovery import discovery_node
from graph.nodes.order_tracking import order_tracking_node
from graph.nodes.router import router_node
from graph.nodes.validation import validation_node
from graph.state import AgentState


def _route_from_router(state: AgentState) -> str:
    next_node = state.get("next_node", "end")
    if next_node == "end":
        return END
    return next_node


def build_graph():
    builder = StateGraph(AgentState)

    builder.add_node("router", router_node)
    builder.add_node("discovery", discovery_node)
    builder.add_node("cart_manager", cart_manager_node)
    builder.add_node("validation", validation_node)
    builder.add_node("checkout", checkout_node)
    builder.add_node("order_tracking", order_tracking_node)

    builder.set_entry_point("router")

    builder.add_conditional_edges(
        "router",
        _route_from_router,
        {
            "discovery": "discovery",
            "cart_manager": "cart_manager",
            "validation": "validation",
            "checkout": "checkout",
            "order_tracking": "order_tracking",
            END: END,
        },
    )

    builder.add_edge("discovery", "router")
    builder.add_edge("cart_manager", "router")
    builder.add_edge("validation", "router")
    builder.add_edge("checkout", END)
    builder.add_edge("order_tracking", END)

    checkpointer = MemorySaver()
    return builder.compile(checkpointer=checkpointer)
