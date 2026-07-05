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

    try:
        from graph.llm import get_llm
        from pydantic import BaseModel, Field

        class TrackingSummary(BaseModel):
            voice_prompt: str = Field(description="A short, conversational voice response explaining the order status to the user.")

        llm = get_llm().with_structured_output(TrackingSummary)
        language_directive = "Reply in the same language the customer prefers (English, Sinhala, Tamil, or Tanglish). "
        
        # Determine language directive from state if available
        preferred_language = str(state.get("preferred_language") or "").lower()
        if preferred_language == "si":
            language_directive = "Write the voice response in clear, friendly Sinhala (Sinhala script). Keep names and URLs as-is."
        elif preferred_language == "ta":
            language_directive = "Write the voice response in clear, friendly Tamil (Tamil script). Keep names and URLs as-is."

        summary = llm.invoke([
            {
                "role": "system", 
                "content": f"You are a Kapruka shopping agent. Read the provided JSON order tracking data and write a short, friendly voice response (max 2 sentences) summarizing the status of the user's order. Mention the most recent progress step or the final status. Do not read out all the details, just give the key takeaway. {language_directive}"
            },
            {
                "role": "user",
                "content": f"Order Number: {order_number}\nTracking Data: {tracking}"
            }
        ])
        voice_prompt = summary.voice_prompt
    except Exception as e:
        logger.error("Failed to generate tracking summary: %s", e)
        voice_prompt = (
            f"Here's the latest on order {order_number} — it's {status}. "
            "You can see the full timeline on your screen."
        )

    return {
        "ui_action": {
            "action": "show_order_tracking",
            "payload": {
                "order_number": order_number,
                "tracking": tracking,
            },
        },
        "voice_prompt": voice_prompt,
        "next_node": "end",
    }
