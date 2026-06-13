# Project Specification: Kapruka AI Shopping Agent (Agent Challenge 2026)

---

## 1. Project Overview & Winning Criteria

We are building a highly visual, full-screen conversational shopping agent for the Kapruka Agent Challenge (deadline: June 30, 2026). The goal is to replace traditional e-commerce flows with an autonomous, natural-language voice and chat interface.

**Core Directives for the Coding Agent:**
- **Visuals over Text:** Render rich UI components (carousels, cards, carts). Do not dump raw Markdown links to the user.
- **Accuracy:** Zero hallucinations on products or prices. Implement strict LangGraph state management for the shopping cart.
- **Advanced Logic:** Successfully handle multi-item carts, delivery constraints (e.g., perishable cakes cannot go to distant cities), and generate a secure click-to-pay link.
- **Localization:** Support English, Sinhala, Tamil, and Tanglish fluidly.

---

## 2. Tech Stack (Strict Constraints)

- **Frontend (Client):** React, Vite, TypeScript, TailwindCSS.
  - **CRITICAL:** Do **NOT** use Next.js. This must be a pure Single Page Application (SPA) to handle raw PCM audio buffers and WebSocket connections without SSR hydration mismatches.
- **Backend (Server):** Python, FastAPI.
- **Agent Orchestration:** LangGraph (Python) for strict state-machine routing.
- **E-Commerce Integration:** Kapruka Public MCP Server (`https://mcp.kapruka.com/mcp`).

---

## 3. Environment Variables

All secrets must be loaded from a `.env` file. Create a `.env.example` as a template.

```env
GEMINI_API_KEY=
KAPRUKA_MCP_URL=https://mcp.kapruka.com/mcp
```

---

## 4. Folder Structure

```
kapruka-agent/
├── backend/
│   ├── main.py                     # FastAPI application initialization
│   ├── graph/
│   │   ├── state.py                # AgentState TypedDict & Pydantic schemas
│   │   ├── graph.py                # LangGraph compilation and workflow definition
│   │   └── nodes/
│   │       ├── router.py           # Intent classification node (gemini-3.5-flash)
│   │       ├── discovery.py        # MCP wrapper execution node
│   │       ├── cart_manager.py     # Pure Python logic for adding/removing items
│   │       ├── validation.py       # Delivery date & location constraint validation
│   │       └── checkout.py         # Final order token generation
│   ├── mcp/
│   │   └── kapruka_tools.py        # All 7 synchronous wrappers for the Kapruka MCP server
│   ├── live/
│   │   ├── gemini_client.py        # Manages the upstream WebSocket connection to Gemini Live API
│   │   └── connection_pool.py      # Tracks active user sessions, graph states, and thread IDs
│   ├── websockets/
│   │   └── stream_handler.py       # Single unified /ws/stream/{session_id} route
│   ├── .env
│   ├── .env.example
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ProductCarousel.tsx  # Renders search results natively
│   │   │   ├── CartDrawer.tsx       # Slide-out interactive checkout tray
│   │   │   ├── CheckoutCard.tsx     # Displays payment link and validation errors
│   │   │   └── VoiceIndicator.tsx   # Dynamic visualizer for audio state
│   │   ├── hooks/
│   │   │   ├── useAudioSession.ts   # COMBINED hook: mic capture + raw PCM speaker playback in one AudioContext
│   │   │   └── useLiveAgent.ts      # Manages single WebSocket lifecycle and routes inbound JSON envelopes
│   │   ├── App.tsx                  # Full-screen conversational window layout
│   │   └── main.tsx
│   ├── index.html
│   ├── vite.config.ts
│   ├── tsconfig.json
│   └── package.json
├── .gitignore
└── README.md
```

---

## 5. Architecture: Unified WebSocket & Session State

### 5.1 Connection Pool (`backend/live/connection_pool.py`)

Session memory is non-negotiable. The backend must maintain a stateful mapping of all connected clients so LangGraph never loses cart context between voice turns.

```python
# connection_pool.py must enforce this exact structure per active client
sessions: dict[str, dict] = {
    "session_id": {
        "live_session": "<BidiGenerateContent object>",   # Model 1 Live API session
        "langgraph_thread_id": "uuid-string",             # Used for LangGraph checkpointing
        "agent_state": AgentState                         # Full TypedDict state (cart, delivery, checkout)
    }
}
```

### 5.2 Multiplexed WebSocket Protocol (`/ws/stream/{session_id}`)

**Do NOT use separate sockets for audio and UI.** A single endpoint handles everything. Mixing them on two connections introduces race conditions where a product carousel renders before the voice says "here are the cakes."

**Outbound (Client → Server):**
Always raw binary PCM audio chunks. No envelope needed.

**Inbound (Server → Client):**
Always JSON envelopes. Two types:

```typescript
// Audio packet — base64-encoded raw PCM from Gemini Live
{ "type": "audio", "data": "<base64 PCM chunk>" }

// UI event packet — triggers React component rendering
{ "type": "ui", "action": "show_products" | "update_cart" | "show_checkout", "payload": { ... } }
```

---

## 6. The Two-Model Architecture

### Model 1 — The "Front Desk" (Voice Layer)

- **Model string:** `gemini-3.1-flash-live-preview`
- **Protocol:** Gemini Live API BidiGenerateContent WebSocket
- **Config:**
  ```python
  responseModalities: ["AUDIO"]
  thinkingLevel: "minimal"   # lowest latency for real-time voice
  systemInstruction: "<Sinhala/Tanglish persona prompt>"
  ```
- **Role:** Listens to user audio, handles interruptions, speaks back. Does **no** backend reasoning.
- **Single registered tool:** `send_intent_to_backend(intent_text: str)`
  - When triggered, Model 1 enters a waiting state until it receives the tool response.

### Model 2 — The "Backend Manager" (Logic Layer)

- **Model string:** `gemini-3.5-flash`
- **Protocol:** Standard Gemini API via LangChain
- **Role:** Receives the transcribed intent, accesses Kapruka MCP tools, validates delivery constraints, and updates LangGraph state.
- **Output (strict JSON):**
  ```json
  {
    "ui_action": { "action": "show_products", "payload": { "products": [ ... ] } },
    "voice_prompt": "I found three chocolate cakes available for delivery to Kadawatha."
  }
  ```

---

## 7. Phase 3 Handoff: The Pause/Resume Mechanism (Critical)

This is the most complex part of the system. Implement it exactly as described.

When Model 1 emits a tool call for `send_intent_to_backend`, FastAPI must execute the following 5-step sequence:

**Step 1 — Detect the tool call:**
```python
# FastAPI receives a BidiGenerateContentServerContent message
if message.tool_call:
    function_call = message.tool_call.function_calls[0]
    assert function_call.name == "send_intent_to_backend"
    intent_text = function_call.args["intent_text"]
    call_id = function_call.id   # SAVE THIS — required for Step 4
```

**Step 2 — Freeze audio upstream:**
Stop forwarding microphone PCM to the Live session while LangGraph runs.
Model 1 is already in a waiting state — it will not respond until it receives a `tool_response`.

**Step 3 — Run LangGraph (Model 2):**
```python
session = connection_pool.sessions[session_id]

result = await langgraph_app.ainvoke(
    {
        **session["agent_state"],
        "messages": session["agent_state"]["messages"] + [HumanMessage(content=intent_text)]
    },
    config={"configurable": {"thread_id": session["langgraph_thread_id"]}}
)

# Update the persisted state in the connection pool
session["agent_state"] = result

ui_action    = result["ui_action"]      # send to React frontend
voice_prompt = result["voice_prompt"]   # return to Model 1
```

**Step 4 — Return the tool response to Model 1:**
```python
# Send a BidiGenerateContentClientContent message resolving the tool call
await live_session.send(tool_response={
    "function_responses": [{
        "id": call_id,       # Must match the call_id from Step 1
        "name": "send_intent_to_backend",
        "response": { "result": voice_prompt }
    }]
})
# Model 1 now reads voice_prompt aloud to the user
```

**Step 5 — Emit the UI event to React:**
```python
# Over the same /ws/stream/{session_id} connection, send the JSON envelope
await websocket.send_json({
    "type": "ui",
    "action": ui_action["action"],
    "payload": ui_action["payload"]
})
# React renders ProductCarousel, CartDrawer, or CheckoutCard
```

> **Order matters:** Always send Step 4 (voice) before Step 5 (UI) so the spoken response and visual update are synchronised from the user's perspective.

---

## 8. LangGraph State Machine

### AgentState

```python
from typing import TypedDict, List, Dict, Any, Optional

class AgentState(TypedDict):
    messages:      list                  # Full conversation history
    cart:          List[Dict[str, Any]]  # [{"product_id": "123", "quantity": 1, "perishable_flag": True, "price": 4500}]
    delivery_info: Dict[str, str]        # {"city": "Kadawatha", "date": "2026-06-25"}
    checkout_info: Dict[str, Any]        # {"recipient": {}, "sender": {"name": "Jakshigan", "phone": "..."}, "gift_message": ""}
    ui_action:     Dict[str, Any]        # Populated by each node for the frontend
    voice_prompt:  str                   # Populated by each node for Model 1 to speak
```

### Nodes

| Node | Model | Description |
|---|---|---|
| **Router** | gemini-3.5-flash | Classifies intent → Discovery, CartManager, Validation, or Checkout |
| **Discovery** | gemini-3.5-flash | Calls `kapruka_search_products` or `kapruka_get_product` via MCP |
| **Cart Manager** | **Pure Python — NO LLM** | Reads current `cart` list from state, applies add/remove mutation, returns updated list. The LLM must never manage cart quantities directly. |
| **Validation** | gemini-3.5-flash | Calls `kapruka_check_delivery`. If perishable constraint fails, injects a voice_prompt asking the user to change the date or city. Loops back to Router. |
| **Checkout** | gemini-3.5-flash | Calls `kapruka_create_order`, returns 60-minute click-to-pay URL |

---

## 9. Kapruka MCP Tools Registry

The FastAPI backend must wrap all 7 endpoints by connecting to `https://mcp.kapruka.com/mcp` via `mcp-remote`. Expose them as synchronous Python functions callable by LangGraph nodes.

| Tool Name | Parameters | Description |
|---|---|---|
| `kapruka_search_products` | `q, category?, price_min?, price_max?, in_stock?, sort?` | Search the catalog by keyword with filters |
| `kapruka_get_product` | `product_id` | Full product details: price, stock, variants, images, shipping |
| `kapruka_list_categories` | _(none)_ | Top-level category names with browse URLs |
| `kapruka_list_delivery_cities` | `query` | Search delivery network by name or vernacular alias (up to 50 matches) |
| `kapruka_check_delivery` | `product_id, city, date` | Verify deliverability; returns flat LKR rate and perishable warning |
| `kapruka_create_order` | `cart, delivery_info, checkout_info` | Create guest-checkout order; returns 60-minute click-to-pay URL |
| `kapruka_track_order` | `order_number` | Returns status, recipient, items, and timestamped delivery progress |

---

## 10. Implementation Phases

> **CRITICAL RULE FOR CURSOR:** Complete and verify each phase before beginning the next. Do not scaffold later phases while earlier phases are untested.

### Phase 1 — FastAPI Base & MCP Setup

1. Initialize FastAPI project with folder structure from Section 4.
2. Load all secrets from `.env`.
3. Implement all 7 synchronous Python wrappers in `backend/mcp/kapruka_tools.py` connecting to the Kapruka MCP server via `mcp-remote`.
4. Write a standalone test script (`test_mcp.py`) that calls `kapruka_search_products(q="chocolate cake")` and prints the result.

**Do not proceed to Phase 2 until `test_mcp.py` returns real Kapruka products.**

### Phase 2 — LangGraph & State Architecture (Model 2)

1. Define `AgentState` in `backend/graph/state.py` exactly as specified in Section 8.
2. Implement all 5 nodes in `backend/graph/nodes/`. The Cart Manager node must be pure Python with no LLM call.
3. Compile the graph in `backend/graph/graph.py`.
4. Implement `connection_pool.py` with the exact session structure from Section 5.1.
5. Write a local text test (`test_graph.py`) using a hardcoded intent:
   ```python
   intent_text = "I want to send a chocolate cake to Kadawatha on 2026-06-25"
   ```
   Verify the graph returns real products, validates delivery, and builds a cart without hallucinating.

**Do not proceed to Phase 3 until `test_graph.py` passes end-to-end with real MCP data.**

### Phase 3 — Gemini Live API & Multiplexed WebSocket (Model 1)

1. Implement `backend/live/gemini_client.py` to open a `gemini-3.1-flash-live-preview` BidiGenerateContent session with config from Section 6.
2. Implement `backend/websockets/stream_handler.py` exposing `/ws/stream/{session_id}`.
3. Implement the 5-step pause/resume handoff from Section 7 **exactly as specified**, including saving and reusing `call_id`.
4. Ensure UI JSON envelopes are sent after the tool response (Step 5 after Step 4).

### Phase 4 — Frontend UI (React + Vite)

1. Initialize project with Vite + React + TypeScript + TailwindCSS. No Next.js.
2. Implement `useAudioSession.ts`: mic capture (16kHz PCM) and speaker playback must share a **single `AudioContext`** instance. Include a PCM playback queue to prevent audio clicking and gaps.
3. Implement `useLiveAgent.ts`: manages the `/ws/stream/{session_id}` WebSocket, routes inbound `type: "audio"` packets to `useAudioSession` and `type: "ui"` packets to React state.
4. Build `ProductCarousel`, `CartDrawer`, `CheckoutCard`, and `VoiceIndicator` components that react to inbound UI JSON envelopes.
5. `App.tsx` must be full-screen, mobile-responsive, and render the correct component based on the current `ui_action`.
