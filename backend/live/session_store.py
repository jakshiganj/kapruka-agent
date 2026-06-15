"""Optional Redis-backed persistence for agent session state.

Gated by REDIS_URL: when unset, every function is a no-op and the app behaves
exactly as the in-memory-only version (local dev needs no Redis). When set,
carts/delivery/checkout state survive backend restarts and are shared across
workers — important for hosted deploys (e.g. Render).
"""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.messages import messages_from_dict, messages_to_dict

from config import settings

logger = logging.getLogger(__name__)

_PREFIX = "kapruka:session:"
_TTL_SECONDS = 60 * 60 * 24  # 24h

_client: Any = None


def is_enabled() -> bool:
    return bool(settings.redis_url)


async def init_redis() -> None:
    """Connect the shared async Redis client (called once at app startup)."""
    global _client
    if not settings.redis_url:
        logger.info("REDIS_URL not set — session persistence disabled (in-memory only).")
        return
    try:
        import redis.asyncio as aioredis

        _client = aioredis.from_url(
            settings.redis_url,
            decode_responses=True,
            max_connections=20,
            socket_timeout=5.0,
            socket_connect_timeout=5.0,
        )
        await _client.ping()
        logger.info("Redis session store connected.")
    except Exception:
        logger.exception("Redis connection failed; falling back to in-memory sessions.")
        _client = None


async def close_redis() -> None:
    global _client
    if _client is not None:
        try:
            await _client.aclose()
        except Exception:
            logger.exception("Error closing Redis client")
        _client = None


def _serialize(state: dict[str, Any]) -> str:
    out: dict[str, Any] = {}
    for key, value in state.items():
        if key == "messages":
            continue
        out[key] = value
    try:
        out["messages"] = messages_to_dict(state.get("messages") or [])
    except Exception:
        out["messages"] = []
    return json.dumps(out, default=str)


async def save_agent_state(session_id: str, state: dict[str, Any]) -> None:
    if _client is None or not state:
        return
    try:
        await _client.set(_PREFIX + session_id, _serialize(state), ex=_TTL_SECONDS)
    except Exception:
        logger.exception("Failed to persist session %s to Redis", session_id)


async def load_agent_state(session_id: str) -> dict[str, Any] | None:
    if _client is None:
        return None
    try:
        raw = await _client.get(_PREFIX + session_id)
    except Exception:
        logger.exception("Failed to load session %s from Redis", session_id)
        return None
    if not raw:
        return None
    try:
        data = json.loads(raw)
        message_dicts = data.pop("messages", []) or []
        data["messages"] = messages_from_dict(message_dicts) if message_dicts else []
        return data
    except Exception:
        logger.exception("Failed to deserialize session %s", session_id)
        return None
