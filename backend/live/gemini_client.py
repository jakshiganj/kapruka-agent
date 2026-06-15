"""Gemini Live API (Model 1) session wrapper."""

from __future__ import annotations

import asyncio
import logging
from contextlib import suppress
from typing import Any, AsyncIterator

from google import genai
from google.genai import types

from config import settings

logger = logging.getLogger(__name__)

LIVE_MODEL = "gemini-3.1-flash-live-preview"
LIVE_CONNECT_ATTEMPTS = 3
LIVE_CONNECT_OPEN_TIMEOUT = 30.0
LIVE_CONNECT_RETRY_DELAY = 2.0

SYSTEM_INSTRUCTION = """You are Kapruka's warm, witty shopping assistant for Sri Lankan customers.
Your name is Kapru — you help people send gifts across Sri Lanka with genuine care.

Language: Mirror the user. Fluent in English, Sinhala (සිංහල), Tamil, and Tanglish.
If they mix languages ("machan, cake ekak Kadawathata"), understand naturally and hand off clearly.
Use occasional Sinhala warmth when speaking English ("stuti!", "perfect!") — never forced.

You are the voice front desk only — you do NOT search products, manage carts, or create orders yourself.
When the user wants to shop, find gifts, check delivery, add another item, or checkout, you MUST call
send_intent_to_backend with a clear summary (products, city, date YYYY-MM-DD, recipient, phone, address,
sender, optional gift message).

If the user points at results on screen ("add the lavender one", "second cake", "that one"), repeat the
EXACT product name from their request in intent_text so the backend can match the carousel.
They can also tap a product on screen to add it directly — you do not need a backend call for taps alone.
When products are shown but nothing is in the cart yet, guide them to tap one or name it — do NOT assume
the first result is in their cart.

If they want a NEW category ("also add flowers", "I want flowers", "search for hampers"), put that new
search term in intent_text and call send_intent_to_backend again — never assume the old carousel is still
the active search.

For product searches, intent_text MUST be the bare product keywords only — never a sentence or a
third-person summary. Say "chocolates", NOT "user wants to look for chocolates". Say "red roses",
NOT "the customer would like to find red roses". Drop filler like "user wants", "looking for",
"I'd like", "show me". Keep delivery/checkout intents short too (e.g. "Delivery to Kadawatha on
2026-06-25").

After something is in the cart, ask whether they'd like more gifts or to proceed to checkout / give delivery details.

After you show products, if the user gives a delivery city and date (same turn or next), you MUST call
send_intent_to_backend again with the city and ISO date — that triggers Kapruka delivery validation.
Example follow-up intent: "Delivery to Kadawatha on 2026-06-25".
Do not skip the backend call just because products are already on screen.
After delivery is validated, if the user gives checkout details or asks to pay — call the backend again.
Never say the order is placed or paid until the backend confirms a checkout link was created.
Delivery validation ≠ order placed.

Personality: Encouraging, concise, celebratory at checkout. Help undecided shoppers compare options briefly.
Keep spoken replies under ~3 sentences unless the user asks for more."""

SEND_INTENT_TOOL = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="send_intent_to_backend",
            description=(
                "Send shopping intent to Kapruka backend: product search, add-to-cart (user must pick a product first), "
                "delivery validation, or checkout/payment link. Call when user names a product to add, gives city/date, "
                "recipient details, gift message, or asks to checkout."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "intent_text": types.Schema(
                        type=types.Type.STRING,
                        description=(
                            "Concise machine intent — NOT a sentence and NOT third person. "
                            "For searches use bare product keywords only: 'chocolates', 'red roses', "
                            "'birthday cake' (never 'user wants to look for chocolates'). "
                            "For other actions: exact product name to add, delivery city + date "
                            "(YYYY-MM-DD), checkout request, recipient name/phone/address, sender name, "
                            "gift message. Keep original-language names when given in Sinhala/Tanglish."
                        ),
                    )
                },
                required=["intent_text"],
            ),
        )
    ]
)


def build_live_config() -> types.LiveConnectConfig:
    return types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        thinking_config=types.ThinkingConfig(
            thinking_level=types.ThinkingLevel.MINIMAL,
        ),
        system_instruction=SYSTEM_INSTRUCTION,
        tools=[SEND_INTENT_TOOL],
        input_audio_transcription=types.AudioTranscriptionConfig(),
        output_audio_transcription=types.AudioTranscriptionConfig(),
    )


class GeminiLiveSession:
    """Wraps a persistent google-genai Live API AsyncSession."""

    def __init__(self) -> None:
        self._client = genai.Client(
            api_key=settings.gemini_api_key,
            http_options=types.HttpOptions(
                async_client_args={
                    "open_timeout": LIVE_CONNECT_OPEN_TIMEOUT,
                    "close_timeout": 10,
                }
            ),
        )
        self._connect_ctx: Any = None
        self.session: Any = None
        self._queue: asyncio.Queue[Any | None] = asyncio.Queue()
        self._receiver_task: asyncio.Task[None] | None = None
        self._closed = False
        self._activity_open = False

    @property
    def is_connected(self) -> bool:
        return self.session is not None and not self._closed

    async def _mark_disconnected(self, exc: Exception, *, context: str) -> None:
        if not self._closed:
            logger.warning("Live session %s: %s", context, exc)
        self._closed = True
        self._activity_open = False

    async def _cleanup_failed_connect(self) -> None:
        ctx = self._connect_ctx
        self._connect_ctx = None
        self.session = None
        if ctx is not None:
            with suppress(Exception):
                await ctx.__aexit__(None, None, None)

    async def connect(self) -> None:
        if self.session is not None:
            return

        last_error: Exception | None = None
        for attempt in range(1, LIVE_CONNECT_ATTEMPTS + 1):
            try:
                self._connect_ctx = self._client.aio.live.connect(
                    model=LIVE_MODEL,
                    config=build_live_config(),
                )
                self.session = await self._connect_ctx.__aenter__()
                self._receiver_task = asyncio.create_task(
                    self._receiver_loop(),
                    name="gemini-live-receiver",
                )
                logger.info("Gemini Live session connected (%s)", LIVE_MODEL)
                return
            except (TimeoutError, asyncio.TimeoutError, OSError) as exc:
                last_error = exc
                await self._cleanup_failed_connect()
                logger.warning(
                    "Gemini Live connect attempt %s/%s failed: %s",
                    attempt,
                    LIVE_CONNECT_ATTEMPTS,
                    exc,
                )
                if attempt < LIVE_CONNECT_ATTEMPTS:
                    await asyncio.sleep(LIVE_CONNECT_RETRY_DELAY)
                    continue
            except Exception:
                await self._cleanup_failed_connect()
                raise

        raise TimeoutError(
            "Gemini Live timed out during the WebSocket handshake. "
            "Verify GEMINI_API_KEY in backend/.env, check internet access, "
            "and disable VPN/firewall blocking Google APIs."
        ) from last_error

    async def _receiver_loop(self) -> None:
        """Continuously read from Gemini so the Live socket stays alive during handoffs."""
        try:
            while not self._closed and self.session is not None:
                try:
                    async for message in self.session.receive():
                        await self._queue.put(message)
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    if self._closed:
                        break
                    logger.warning("Live receive ended: %s", exc)
                    self._closed = True
                    break
        finally:
            await self._queue.put(None)

    async def close(self) -> None:
        self._closed = True
        self._activity_open = False
        if self._receiver_task is not None:
            self._receiver_task.cancel()
            try:
                await self._receiver_task
            except asyncio.CancelledError:
                pass
            self._receiver_task = None
        if self._connect_ctx is not None:
            await self._connect_ctx.__aexit__(None, None, None)
            self._connect_ctx = None
            self.session = None
            logger.info("Gemini Live session closed")

    async def send_pcm_audio(self, pcm_chunk: bytes) -> None:
        if not self.is_connected:
            return
        try:
            await self.session.send_realtime_input(
                audio=types.Blob(
                    data=pcm_chunk,
                    mime_type="audio/pcm;rate=16000",
                )
            )
        except Exception as exc:
            await self._mark_disconnected(exc, context="audio send failed")

    async def end_activity_if_open(self) -> None:
        """Close an open manual VAD turn before handoff or shutdown."""
        if not self._activity_open:
            return
        await self.send_activity_end()

    async def send_activity_start(self) -> None:
        if not self.is_connected or self._activity_open:
            return
        try:
            await self.session.send_realtime_input(activity_start=types.ActivityStart())
            self._activity_open = True
            logger.debug("Sent activity_start")
        except Exception as exc:
            await self._mark_disconnected(exc, context="activity_start failed")

    async def send_activity_end(self) -> None:
        if not self.is_connected or not self._activity_open:
            return
        try:
            await self.session.send_realtime_input(activity_end=types.ActivityEnd())
            logger.info("Sent activity_end")
        except Exception as exc:
            await self._mark_disconnected(exc, context="activity_end failed")
        finally:
            self._activity_open = False

    async def send_tool_response(
        self,
        *,
        call_id: str,
        name: str,
        result: str,
    ) -> None:
        if not self.is_connected:
            logger.warning("Skipping tool response — Live session disconnected")
            return
        try:
            await self.session.send_tool_response(
                function_responses=types.FunctionResponse(
                    id=call_id,
                    name=name,
                    response={"result": result},
                )
            )
        except Exception as exc:
            await self._mark_disconnected(exc, context="tool response failed")

    async def receive_messages(self) -> AsyncIterator[types.LiveServerMessage]:
        while True:
            message = await self._queue.get()
            if message is None:
                break
            yield message
