from __future__ import annotations

import logging
from typing import Any

from graph.state import AgentState
from kapruka_mcp.kapruka_tools import KaprukaMCPError, kapruka_track_order

logger = logging.getLogger(__name__)


def order_tracking_node(state: AgentState) -> dict[str, Any]:
    payload = (state.get("ui_action") or {}).get("payload") or {}
    order_number = str(payload.get("order_number") or "").strip()

    if not order_number:
        return {
            "voice_prompt": (
                "Sure — what's your Kapruka order number? It's in the confirmation "
                "email you received after paying."
            ),
            "next_node": "end",
        }

    try:
        logger.info("Calling kapruka_track_order for %s", order_number)
        tracking = kapruka_track_order(order_number)
    except KaprukaMCPError as exc:
        message = str(exc).removeprefix("Error:").strip()
        return {
            "voice_prompt": (
                f"I couldn't find order {order_number}. {message} "
                "Please double-check the number from your confirmation email."
            ),
            "next_node": "end",
        }

    status = (
        tracking.get("status")
        or tracking.get("order_status")
        or (tracking.get("order") or {}).get("status")
        or "in progress"
    )

    return {
        "ui_action": {
            "action": "show_order_tracking",
            "payload": {
                "order_number": order_number,
                "tracking": tracking,
            },
        },
        "voice_prompt": (
            f"Here's the latest on order {order_number} — it's {status}. "
            "You can see the full timeline on your screen."
        ),
        "next_node": "end",
    }
