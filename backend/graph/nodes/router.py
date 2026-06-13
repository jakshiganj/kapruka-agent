from __future__ import annotations

import re
from typing import Any

from langchain_core.messages import HumanMessage

from graph.llm import get_llm
from graph.state import AgentState, RouterDecision


DATE_PATTERN = re.compile(r"\b(20\d{2}-\d{2}-\d{2})\b")
CITY_DATE_PATTERN = re.compile(
    r"\bto\s+([A-Za-z]+)\s+on\s+(20\d{2}-\d{2}-\d{2})\b",
    re.IGNORECASE,
)
SEARCH_QUERY_PATTERN = re.compile(
    r"\bsend(?:\s+a|\s+an)?\s+(.+?)\s+to\s+[A-Za-z]+\s+on\s+20\d{2}-\d{2}-\d{2}\b",
    re.IGNORECASE,
)


def _latest_user_text(state: AgentState) -> str:
    for message in reversed(state["messages"]):
        if isinstance(message, HumanMessage):
            return str(message.content)
    return ""


def _deterministic_next(state: AgentState) -> str | None:
    cart = state.get("cart") or []
    ui_action = state.get("ui_action") or {}
    delivery_info = state.get("delivery_info") or {}
    validated = delivery_info.get("validated") == "true"

    if not ui_action.get("payload", {}).get("products") and not cart:
        return "discovery"
    if ui_action.get("payload", {}).get("products") and not cart:
        return "cart_manager"
    if cart and delivery_info.get("city") and delivery_info.get("date") and not validated:
        return "validation"
    if cart and validated:
        return "end"
    return None


def _extract_delivery_from_text(user_text: str) -> dict[str, str]:
    delivery: dict[str, str] = {}
    matches = CITY_DATE_PATTERN.findall(user_text)
    if matches:
        city, date = matches[-1]
        delivery["city"] = city.strip()
        delivery["date"] = date
    else:
        date_match = DATE_PATTERN.search(user_text)
        if date_match:
            delivery["date"] = date_match.group(1)
    return delivery


def _extract_search_query(user_text: str) -> str | None:
    match = SEARCH_QUERY_PATTERN.search(user_text)
    if match:
        return match.group(1).strip()
    return None


def router_node(state: AgentState) -> dict[str, Any]:
    user_text = _latest_user_text(state)
    delivery_info = dict(state.get("delivery_info") or {})
    extracted = _extract_delivery_from_text(user_text)
    delivery_info.update({k: v for k, v in extracted.items() if v})

    search_query = _extract_search_query(user_text)
    ui_action = dict(state.get("ui_action") or {})
    if search_query:
        payload = dict(ui_action.get("payload") or {})
        payload["search_query"] = search_query
        ui_action["payload"] = payload

    deterministic = _deterministic_next({**state, "delivery_info": delivery_info})
    if deterministic:
        updates: dict[str, Any] = {"next_node": deterministic, "delivery_info": delivery_info}
        if search_query:
            updates["ui_action"] = ui_action
        return updates
    llm = get_llm().with_structured_output(RouterDecision)
    decision: RouterDecision = llm.invoke(
        [
            {
                "role": "system",
                "content": (
                    "You route a Kapruka shopping agent. Extract delivery city, delivery date "
                    "(YYYY-MM-DD), and a product search query from the user message. "
                    "For a shopping request with product + city + date, set next_node to discovery."
                ),
            },
            {"role": "user", "content": user_text},
        ]
    )

    if decision.delivery_city:
        delivery_info["city"] = decision.delivery_city
    if decision.delivery_date:
        delivery_info["date"] = decision.delivery_date

    date_match = DATE_PATTERN.search(user_text)
    if date_match and "date" not in delivery_info:
        delivery_info["date"] = date_match.group(1)

    updates: dict[str, Any] = {
        "next_node": decision.next_node,
        "delivery_info": delivery_info,
    }
    if decision.voice_prompt:
        updates["voice_prompt"] = decision.voice_prompt
    if decision.search_query:
        payload = dict((state.get("ui_action") or {}).get("payload") or {})
        payload["search_query"] = decision.search_query
        updates["ui_action"] = {
            "action": state.get("ui_action", {}).get("action", ""),
            "payload": payload,
        }

    if not updates.get("next_node"):
        updates["next_node"] = "discovery"

    return updates
