"""Synchronous wrappers for the Kapruka public MCP server."""

from __future__ import annotations

import asyncio
import json
import threading
from contextlib import AsyncExitStack
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from config import settings

PERISHABLE_PREFIXES = ("CAKE", "FLOWER", "COMBO")


class KaprukaMCPError(Exception):
    """Raised when Kapruka MCP returns an error string."""


class _KaprukaMCPClient:
    """Persistent async MCP session with sync entry points."""

    def __init__(self) -> None:
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._ready = threading.Event()
        self._session: ClientSession | None = None
        self._exit_stack: AsyncExitStack | None = None

    def _run_loop(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._ready.set()
        self._loop.run_forever()

    def _ensure_loop(self) -> asyncio.AbstractEventLoop:
        if self._loop is None or not self._loop.is_running():
            self._ready.clear()
            self._thread = threading.Thread(target=self._run_loop, daemon=True)
            self._thread.start()
            self._ready.wait()
        return self._loop  # type: ignore[return-value]

    async def _connect(self) -> ClientSession:
        if self._session is not None:
            return self._session

        self._exit_stack = AsyncExitStack()
        read_stream, write_stream, _ = await self._exit_stack.enter_async_context(
            streamablehttp_client(settings.kapruka_mcp_url)
        )
        session = await self._exit_stack.enter_async_context(
            ClientSession(read_stream, write_stream)
        )
        await session.initialize()
        self._session = session
        return session

    def _run_coro(self, coro: Any) -> Any:
        loop = self._ensure_loop()
        future = asyncio.run_coroutine_threadsafe(coro, loop)
        return future.result(timeout=120)

    async def _call_tool(self, tool_name: str, params: dict[str, Any]) -> dict[str, Any]:
        session = await self._connect()
        payload = {"params": {**params, "response_format": "json"}}
        result = await session.call_tool(tool_name, payload)

        raw = _extract_result_text(result.content)
        if raw.startswith("Error:") or raw.startswith("No products found"):
            raise KaprukaMCPError(raw)

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise KaprukaMCPError(f"Invalid JSON from {tool_name}: {raw[:200]}") from exc

        if not isinstance(parsed, dict):
            raise KaprukaMCPError(f"Unexpected response type from {tool_name}")
        return parsed

    def call_tool_sync(self, tool_name: str, params: dict[str, Any]) -> dict[str, Any]:
        return self._run_coro(self._call_tool(tool_name, params))


_client = _KaprukaMCPClient()


def _extract_result_text(content: list[Any]) -> str:
    for block in content:
        text = getattr(block, "text", None)
        if text:
            return text.strip()
    return ""


def _call_tool_sync(tool_name: str, **params: Any) -> dict[str, Any]:
    clean = {k: v for k, v in params.items() if v is not None}
    return _client.call_tool_sync(tool_name, clean)


def is_perishable_product(product_id: str) -> bool:
    upper = product_id.upper()
    return any(upper.startswith(prefix) for prefix in PERISHABLE_PREFIXES)


def resolve_delivery_city(user_city: str) -> str:
    """Resolve a user-provided city to a Kapruka canonical city name."""
    result = kapruka_list_delivery_cities(query=user_city, limit=5)
    cities = result.get("cities") or []
    if not cities:
        raise KaprukaMCPError(f"No delivery cities matched '{user_city}'")

    query_lower = user_city.lower()
    for city in cities:
        name = city.get("name", "")
        if name.lower() == query_lower:
            return name
        aliases = city.get("aliases") or []
        if any(query_lower in alias.lower() or alias.lower() in query_lower for alias in aliases):
            return name

    return cities[0]["name"]


def kapruka_search_products(
    q: str,
    *,
    category: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    in_stock_only: bool = False,
    sort: str = "relevance",
    limit: int = 10,
    cursor: str | None = None,
    currency: str = "LKR",
    include_stubs: bool = False,
) -> dict[str, Any]:
    return _call_tool_sync(
        "kapruka_search_products",
        q=q,
        category=category,
        min_price=min_price,
        max_price=max_price,
        in_stock_only=in_stock_only,
        sort=sort,
        limit=limit,
        cursor=cursor,
        currency=currency,
        include_stubs=include_stubs,
    )


def kapruka_get_product(
    product_id: str,
    *,
    currency: str = "LKR",
    type: str | None = None,
) -> dict[str, Any]:
    return _call_tool_sync(
        "kapruka_get_product",
        product_id=product_id,
        currency=currency,
        type=type,
    )


def kapruka_list_categories(*, depth: int = 1) -> dict[str, Any]:
    return _call_tool_sync("kapruka_list_categories", depth=depth)


def kapruka_list_delivery_cities(
    query: str | None = None,
    *,
    limit: int = 25,
) -> dict[str, Any]:
    return _call_tool_sync(
        "kapruka_list_delivery_cities",
        query=query,
        limit=limit,
    )


def kapruka_check_delivery(
    city: str,
    delivery_date: str | None = None,
    *,
    product_id: str | None = None,
) -> dict[str, Any]:
    return _call_tool_sync(
        "kapruka_check_delivery",
        city=city,
        delivery_date=delivery_date,
        product_id=product_id,
    )


def kapruka_create_order(
    cart: list[dict[str, Any]],
    recipient: dict[str, Any],
    delivery: dict[str, Any],
    sender: dict[str, Any],
    *,
    gift_message: str | None = None,
    currency: str = "LKR",
) -> dict[str, Any]:
    return _call_tool_sync(
        "kapruka_create_order",
        cart=cart,
        recipient=recipient,
        delivery=delivery,
        sender=sender,
        gift_message=gift_message,
        currency=currency,
    )


def kapruka_track_order(order_number: str) -> dict[str, Any]:
    return _call_tool_sync(
        "kapruka_track_order",
        order_number=order_number,
    )


def extract_price_amount(price_field: Any) -> float | None:
    if isinstance(price_field, dict):
        amount = price_field.get("amount")
        if amount is not None:
            return float(amount)
    if isinstance(price_field, (int, float)):
        return float(price_field)
    return None
