"""Synchronous wrappers for the Kapruka public MCP server."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import threading
import time
from concurrent.futures import TimeoutError as FuturesTimeoutError
from collections import deque
from contextlib import AsyncExitStack
from dataclasses import asdict, dataclass, field
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from config import settings

logger = logging.getLogger(__name__)

PERISHABLE_PREFIXES = ("CAKE", "FLOWER", "COMBO")

# Kapruka free tier: 60 req/min/IP across all tools; 30 create_order/hour/IP.
MCP_REQUESTS_PER_MINUTE = 60
MCP_ORDER_LIMIT_PER_HOUR = 30
MCP_READ_CACHE_TTL_SECONDS = 30 * 60  # matches server-side product/category cache
MCP_RATE_LIMIT_RETRIES = 3  # up to 3 retries with exponential backoff
MCP_RATE_LIMIT_BASE_BACKOFF_SECONDS = 1.0
_TRANSIENT_HTTP_MARKERS = ("429", "502", "503", "520", "Too Many Requests")
MCP_MAX_WAIT_SECONDS = 15.0  # fail fast for voice UX if limiter would block longer
MCP_CONNECT_TIMEOUT = 12.0
MCP_CALL_TIMEOUT = 20.0
MCP_RUN_TIMEOUT = 35.0  # max wall time for one sync tool call (connect + call + retry)

READ_TOOLS = frozenset(
    {
        "kapruka_search_products",
        "kapruka_get_product",
        "kapruka_list_categories",
        "kapruka_list_delivery_cities",
        "kapruka_check_delivery",
    }
)
WRITE_TOOLS = frozenset({"kapruka_create_order"})


class KaprukaMCPError(Exception):
    """Raised when Kapruka MCP returns an error string."""


@dataclass
class MCPCallRecord:
    tool: str
    duration_ms: float
    cached: bool
    ok: bool
    detail: str
    at: float = field(default_factory=time.time)


_call_log: deque[MCPCallRecord] = deque(maxlen=200)
_in_flight: dict[str, float] = {}


def _record_call(
    *,
    tool: str,
    duration_ms: float,
    cached: bool,
    ok: bool,
    detail: str,
) -> None:
    record = MCPCallRecord(
        tool=tool,
        duration_ms=duration_ms,
        cached=cached,
        ok=ok,
        detail=detail,
    )
    _call_log.append(record)
    logger.info(
        "MCP #%s %s %s in %.0fms — %s",
        len(_call_log),
        tool,
        "cache" if cached else "network",
        duration_ms,
        detail,
    )


def get_mcp_stats() -> dict[str, Any]:
    """Return recent Kapruka MCP call counters for debugging."""
    from collections import Counter

    network = [r for r in _call_log if not r.cached]
    by_tool = Counter(r.tool for r in network)
    failures = [r for r in _call_log if not r.ok]
    rate_limits = [r for r in failures if "rate limit" in r.detail.lower()]

    return {
        "total_logged": len(_call_log),
        "network_calls": len(network),
        "cache_hits": sum(1 for r in _call_log if r.cached),
        "failures": len(failures),
        "rate_limit_errors": len(rate_limits),
        "in_flight": list(_in_flight.keys()),
        "by_tool": dict(by_tool),
        "recent": [asdict(r) for r in list(_call_log)[-15:]],
        "limits": {
            "requests_per_minute": MCP_REQUESTS_PER_MINUTE,
            "create_order_per_hour": MCP_ORDER_LIMIT_PER_HOUR,
        },
    }


def reset_mcp_stats() -> None:
    _call_log.clear()
    _in_flight.clear()


def _is_transient_http_error(message: str) -> bool:
    return any(marker in message for marker in _TRANSIENT_HTTP_MARKERS)


class _SlidingWindowLimiter:
    """Client-side guard aligned with Kapruka's per-minute / per-hour caps."""

    def __init__(self, max_calls: int, window_seconds: float, *, label: str) -> None:
        self._max_calls = max_calls
        self._window_seconds = window_seconds
        self._label = label
        self._timestamps: deque[float] = deque()

    def _prune(self, now: float) -> None:
        while self._timestamps and now - self._timestamps[0] >= self._window_seconds:
            self._timestamps.popleft()

    async def acquire(self) -> None:
        while True:
            now = time.monotonic()
            self._prune(now)
            if len(self._timestamps) < self._max_calls:
                self._timestamps.append(now)
                return

            wait = self._window_seconds - (now - self._timestamps[0]) + 0.05
            if wait > MCP_MAX_WAIT_SECONDS:
                raise KaprukaMCPError(
                    f"Error: Kapruka {self._label} limit reached. "
                    f"Please wait {int(wait)} seconds."
                )
            logger.info(
                "Kapruka MCP %s limit (%s/%s); waiting %.1fs",
                self._label,
                len(self._timestamps),
                self._max_calls,
                wait,
            )
            await asyncio.sleep(wait)


class _KaprukaMCPClient:
    """Persistent async MCP session with sync entry points."""

    def __init__(self) -> None:
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._ready = threading.Event()
        self._session: ClientSession | None = None
        self._exit_stack: AsyncExitStack | None = None
        self._call_lock: asyncio.Lock | None = None
        self._minute_limiter = _SlidingWindowLimiter(
            MCP_REQUESTS_PER_MINUTE,
            60.0,
            label="60/min",
        )
        self._order_limiter = _SlidingWindowLimiter(
            MCP_ORDER_LIMIT_PER_HOUR,
            3600.0,
            label="30 orders/hour",
        )
        self._cache: dict[str, tuple[dict[str, Any], float]] = {}

    def _run_loop(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._call_lock = asyncio.Lock()
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
        try:
            return await asyncio.wait_for(self._open_session(), timeout=MCP_CONNECT_TIMEOUT)
        except asyncio.TimeoutError as exc:
            await self._reset_session()
            raise KaprukaMCPError(
                "Error: Kapruka MCP connection timed out. Please try again in a few seconds."
            ) from exc

    async def _open_session(self) -> ClientSession:
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

    async def _reset_session(self) -> None:
        """Drop the current MCP session; reconnect lazily on the next tool call."""
        self._session = None
        stack = self._exit_stack
        self._exit_stack = None
        if stack is None:
            return
        try:
            await stack.aclose()
        except Exception as exc:
            # Broken sessions (520, timeout cancel) often fail anyio teardown — orphan is fine.
            logger.warning(
                "Kapruka MCP session teardown skipped (%s); will open a fresh session next call.",
                type(exc).__name__,
            )

    def _run_coro(self, coro: Any, *, timeout: float = MCP_RUN_TIMEOUT) -> Any:
        loop = self._ensure_loop()
        future = asyncio.run_coroutine_threadsafe(coro, loop)
        try:
            return future.result(timeout=timeout)
        except FuturesTimeoutError as exc:
            raise KaprukaMCPError(
                "Error: Kapruka request timed out. Please try again in a few seconds."
            ) from exc
        except asyncio.CancelledError as exc:
            raise KaprukaMCPError(
                "Error: Kapruka request was interrupted. Please try again in a few seconds."
            ) from exc

    def _cache_key(self, tool_name: str, params: dict[str, Any]) -> str:
        return f"{tool_name}:{json.dumps(params, sort_keys=True, default=str)}"

    def _cache_ttl(self, tool_name: str) -> float | None:
        if tool_name in READ_TOOLS:
            return MCP_READ_CACHE_TTL_SECONDS
        return None

    def _get_cached(self, tool_name: str, key: str) -> dict[str, Any] | None:
        ttl = self._cache_ttl(tool_name)
        if ttl is None:
            return None
        cached = self._cache.get(key)
        if not cached:
            return None
        payload, cached_at = cached
        if time.monotonic() - cached_at > ttl:
            self._cache.pop(key, None)
            return None
        return payload

    async def _acquire_limits(self, tool_name: str) -> None:
        assert self._call_lock is not None
        async with self._call_lock:
            await self._minute_limiter.acquire()
            if tool_name in WRITE_TOOLS:
                await self._order_limiter.acquire()

    async def _call_tool(self, tool_name: str, params: dict[str, Any]) -> dict[str, Any]:
        started = time.perf_counter()
        cache_key = self._cache_key(tool_name, params)
        cached = self._get_cached(tool_name, cache_key)
        if cached is not None:
            _record_call(
                tool=tool_name,
                duration_ms=(time.perf_counter() - started) * 1000,
                cached=True,
                ok=True,
                detail="cache hit",
            )
            return cached

        payload = {"params": {**params, "response_format": "json"}}

        last_error: KaprukaMCPError | None = None
        _in_flight[tool_name] = time.monotonic()
        logger.info("Kapruka MCP call starting: %s", tool_name)
        try:
            for attempt in range(MCP_RATE_LIMIT_RETRIES + 1):
                session = await self._connect()
                await self._acquire_limits(tool_name)
                try:
                    result = await asyncio.wait_for(
                        session.call_tool(tool_name, payload),
                        timeout=MCP_CALL_TIMEOUT,
                    )
                except asyncio.TimeoutError:
                    await self._reset_session()
                    last_error = KaprukaMCPError(
                        f"Error: Kapruka {tool_name} timed out after {MCP_CALL_TIMEOUT:.0f}s. "
                        "Please try again in a few seconds."
                    )
                    if attempt < MCP_RATE_LIMIT_RETRIES:
                        backoff = MCP_RATE_LIMIT_BASE_BACKOFF_SECONDS * (2 ** attempt)
                        logger.warning(
                            "Kapruka MCP timeout on %s; retrying in %.1fs (attempt %d/%d)",
                            tool_name,
                            backoff,
                            attempt + 1,
                            MCP_RATE_LIMIT_RETRIES,
                        )
                        await asyncio.sleep(backoff)
                        continue
                    raise last_error
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    message = str(exc) or type(exc).__name__
                    if _is_transient_http_error(message):
                        if "429" in message or "Too Many Requests" in message:
                            last_error = KaprukaMCPError(
                                "Error: Kapruka rate limit reached. Please wait about a minute."
                            )
                        else:
                            last_error = KaprukaMCPError(
                                "Error: Kapruka is temporarily unavailable. Please try again in a few seconds."
                            )
                        if attempt < MCP_RATE_LIMIT_RETRIES:
                            backoff = MCP_RATE_LIMIT_BASE_BACKOFF_SECONDS * (2 ** attempt)
                            logger.warning(
                                "Kapruka MCP transient error on %s (%s); retrying in %.1fs (attempt %d/%d)",
                                tool_name,
                                message.split("\n", 1)[0][:120],
                                backoff,
                                attempt + 1,
                                MCP_RATE_LIMIT_RETRIES,
                            )
                            await asyncio.sleep(backoff)
                            await self._reset_session()
                            continue
                        raise last_error
                    await self._reset_session()
                    raise KaprukaMCPError(
                        f"Error: Kapruka MCP connection failed: {message}"
                    ) from exc

                raw = _extract_result_text(result.content)

                if raw.startswith("Error:"):
                    last_error = KaprukaMCPError(raw)
                    if "rate limit" in raw.lower() and attempt < MCP_RATE_LIMIT_RETRIES:
                        backoff = MCP_RATE_LIMIT_BASE_BACKOFF_SECONDS * (2 ** attempt)
                        logger.warning(
                            "Kapruka MCP server rate limited %s; retrying in %.1fs (attempt %d/%d)",
                            tool_name,
                            backoff,
                            attempt + 1,
                            MCP_RATE_LIMIT_RETRIES,
                        )
                        await asyncio.sleep(backoff)
                        continue
                    raise last_error

                if raw.startswith("No products found"):
                    empty = {"results": [], "message": raw}
                    if self._cache_ttl(tool_name) is not None:
                        self._cache[cache_key] = (empty, time.monotonic())
                    _record_call(
                        tool=tool_name,
                        duration_ms=(time.perf_counter() - started) * 1000,
                        cached=False,
                        ok=True,
                        detail=raw,
                    )
                    return empty

                try:
                    parsed = json.loads(raw)
                except json.JSONDecodeError as exc:
                    raise KaprukaMCPError(f"Invalid JSON from {tool_name}: {raw[:200]}") from exc

                if not isinstance(parsed, dict):
                    raise KaprukaMCPError(f"Unexpected response type from {tool_name}")

                item_count = len(parsed.get("results") or parsed.get("cities") or [])
                detail = f"ok ({item_count} items)"
                if tool_name == "kapruka_list_delivery_cities":
                    detail = f"ok ({item_count} items) query={params.get('query')!r}"

                # Do not cache empty city lookups — retry variants may succeed.
                if tool_name == "kapruka_list_delivery_cities" and not (parsed.get("cities") or []):
                    _record_call(
                        tool=tool_name,
                        duration_ms=(time.perf_counter() - started) * 1000,
                        cached=False,
                        ok=True,
                        detail=detail,
                    )
                    return parsed

                if self._cache_ttl(tool_name) is not None:
                    self._cache[cache_key] = (parsed, time.monotonic())
                _record_call(
                    tool=tool_name,
                    duration_ms=(time.perf_counter() - started) * 1000,
                    cached=False,
                    ok=True,
                    detail=detail,
                )
                return parsed

            if last_error is not None:
                raise last_error
            raise KaprukaMCPError(f"{tool_name} failed without a response")
        except KaprukaMCPError as exc:
            _record_call(
                tool=tool_name,
                duration_ms=(time.perf_counter() - started) * 1000,
                cached=False,
                ok=False,
                detail=str(exc),
            )
            raise
        finally:
            _in_flight.pop(tool_name, None)

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


def _city_search_queries(user_city: str) -> list[str]:
    """Build MCP query variants for fuzzy city lookup (e.g. 'Colombo 7' -> 'Colombo 07')."""
    raw = user_city.strip()
    if not raw:
        return []

    queries: list[str] = [raw]
    collapsed = re.sub(r"\s+", " ", raw)
    if collapsed not in queries:
        queries.append(collapsed)

    nospace = re.sub(r"\s+", "", raw)
    if nospace.lower() not in {q.lower() for q in queries}:
        queries.append(nospace)

    colombo_match = re.match(r"(?i)colombo\s*(\d{1,2})\b", collapsed)
    if colombo_match:
        zone = int(colombo_match.group(1))
        for variant in (
            f"Colombo {zone:02d}",
            f"colombo {zone:02d}",
            f"colombo{zone:02d}",
            f"colombo{zone}",
            str(zone),
        ):
            if variant.lower() not in {q.lower() for q in queries}:
                queries.append(variant)

    return queries


def _city_name_matches(user_city: str, city: dict[str, Any]) -> bool:
    """Return True when user_city clearly refers to a Kapruka delivery zone."""
    query_lower = user_city.lower().strip()
    if not query_lower:
        return False

    name = str(city.get("name", "")).lower()
    if name == query_lower:
        return True
    if len(query_lower) >= 4 and (query_lower in name or name in query_lower):
        return True

    for alias in city.get("aliases") or []:
        alias_lower = str(alias).lower().strip()
        if not alias_lower:
            continue
        if alias_lower == query_lower:
            return True
        for token in re.split(r"[\s,/]+", alias_lower):
            token = token.strip()
            if len(token) < 4:
                continue
            if token == query_lower:
                return True
            if len(token) >= 5 and len(query_lower) >= 5 and (
                token in query_lower or query_lower in token
            ):
                return True
    return False


# Canonical city resolutions are stable, so cache them in-process to avoid
# re-listing delivery cities (multiple MCP calls) on every checkout / re-validation.
_city_resolution_cache: dict[str, str] = {}


def resolve_delivery_city(user_city: str) -> str:
    """Resolve a user-provided city to a Kapruka canonical city name."""
    user_city = user_city.strip()
    if not user_city:
        raise KaprukaMCPError("Delivery city is required")

    cache_key = re.sub(r"\s+", " ", user_city).lower()
    cached_name = _city_resolution_cache.get(cache_key)
    if cached_name:
        return cached_name

    cities: list[dict[str, Any]] = []
    for query in _city_search_queries(user_city):
        result = kapruka_list_delivery_cities(query=query, limit=10)
        cities = result.get("cities") or []
        if cities:
            break

    if not cities:
        raise KaprukaMCPError(
            f"No delivery cities matched '{user_city}'. "
            "Try a Kapruka zone name like 'Colombo 07' or 'Kadawatha'."
        )

    for city in cities:
        if _city_name_matches(user_city, city):
            _city_resolution_cache[cache_key] = city["name"]
            return city["name"]

    # Prefer exact Colombo zone when user gave a number (e.g. "Colombo 7").
    colombo_match = re.match(r"(?i)colombo\s*(\d{1,2})\b", user_city)
    if colombo_match:
        zone = int(colombo_match.group(1))
        target = f"colombo {zone:02d}"
        for city in cities:
            if city.get("name", "").lower() == target:
                _city_resolution_cache[cache_key] = city["name"]
                return city["name"]

    suggestions = ", ".join(city.get("name", "") for city in cities[:5] if city.get("name"))
    raise KaprukaMCPError(
        f"'{user_city}' doesn't match a Kapruka delivery zone closely enough. "
        f"Did you mean: {suggestions}?"
    )


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
    if isinstance(query, str):
        query = query.strip() or None
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
