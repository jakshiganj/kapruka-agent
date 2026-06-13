"""Test the Phase 3 handoff logic without audio (simulates a Live tool call)."""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

from langchain_core.messages import HumanMessage

from live.connection_pool import create_session, get_session
from live.handoff import run_intent_handoff


class FakeWebSocket:
    def __init__(self) -> None:
        self.messages: list[dict] = []

    async def send_json(self, payload: dict) -> None:
        self.messages.append(payload)


class FakeLiveSession:
    def __init__(self) -> None:
        self.tool_responses: list[dict] = []

    async def send_tool_response(self, *, call_id: str, name: str, result: str) -> None:
        self.tool_responses.append(
            {"id": call_id, "name": name, "result": result}
        )

    async def end_activity_if_open(self) -> None:
        pass


async def main() -> None:
    session = create_session()
    websocket = FakeWebSocket()
    live = FakeLiveSession()

    tool_call = SimpleNamespace(
        function_calls=[
            SimpleNamespace(
                name="send_intent_to_backend",
                id="call-test-123",
                args={"intent_text": "I want to send a chocolate cake to Kadawatha on 2026-06-25"},
            )
        ]
    )

    assert not get_session(session["session_id"])["audio_frozen"]

    await run_intent_handoff(
        session_id=session["session_id"],
        live_session=live,
        websocket=websocket,
        tool_call=tool_call,
    )

    pool = get_session(session["session_id"])
    assert not pool["audio_frozen"]
    assert pool["agent_state"]["cart"], "Expected cart in agent_state"
    assert live.tool_responses, "Expected tool response to Model 1"
    assert websocket.messages, "Expected control/UI envelopes to client"
    assert websocket.messages[0]["type"] == "control"
    assert websocket.messages[0]["action"] == "mic_pause"
    assert websocket.messages[-1]["type"] == "control"
    assert websocket.messages[-1]["action"] == "mic_resume"

    # Step 4 before Step 5: tool response recorded before UI send in our implementation
    assert live.tool_responses[0]["result"]
    ui_messages = [m for m in websocket.messages if m.get("type") == "ui"]
    assert ui_messages, "Expected UI envelope to client"
    ui_msg = ui_messages[-1]
    assert ui_msg["type"] == "ui"
    assert ui_msg["action"]

    print(json.dumps({
        "tool_response": live.tool_responses[0],
        "ui_message": ui_msg,
        "cart": pool["agent_state"]["cart"],
        "voice_prompt": pool["agent_state"]["voice_prompt"],
    }, indent=2, default=str))
    print("\nPhase 3 handoff test passed.")


if __name__ == "__main__":
    asyncio.run(main())
