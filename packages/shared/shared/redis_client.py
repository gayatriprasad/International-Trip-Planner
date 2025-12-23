from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

import redis.asyncio as redis


@dataclass(frozen=True)
class RedisConfig:
    url: str
    socket_timeout: float = 1.0
    socket_connect_timeout: float = 1.0
    health_check_interval: int = 15


class RedisClient:
    """
    Shared async Redis client.
    Used by orchestrator + tools.
    """

    def __init__(self, cfg: RedisConfig):
        self._cfg = cfg
        self._client: Optional[redis.Redis] = None

    @classmethod
    def from_env(cls) -> "RedisClient":
        url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        return cls(RedisConfig(url=url))

    def client(self) -> redis.Redis:
        if self._client is None:
            self._client = redis.from_url(
                self._cfg.url,
                decode_responses=True,
                socket_timeout=self._cfg.socket_timeout,
                socket_connect_timeout=self._cfg.socket_connect_timeout,
                health_check_interval=self._cfg.health_check_interval,
            )
        return self._client

    async def ping(self) -> bool:
        try:
            return bool(await self.client().ping())
        except Exception:
            return False

    async def close(self) -> None:
        if self._client is not None:
            await self._client.close()
            self._client = None
