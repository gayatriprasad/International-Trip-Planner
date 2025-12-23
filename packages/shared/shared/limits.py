from __future__ import annotations

import time
from dataclasses import dataclass

import redis.asyncio as redis


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    remaining: int
    limit: int
    reset_in_seconds: int


class RedisRateLimiter:
    """
    Fixed-window rate limiter.
    Key: rl:{user}:{tool}:{epoch_minute}
    """

    def __init__(self, r: redis.Redis, per_minute: int):
        self.r = r
        self.per_minute = per_minute

    async def check(self, user_key: str, tool: str) -> RateLimitResult:
        now = int(time.time())
        epoch_minute = now // 60
        key = f"rl:{user_key}:{tool}:{epoch_minute}"

        count = await self.r.incr(key)
        if count == 1:
            await self.r.expire(key, 75)

        remaining = max(self.per_minute - count, 0)
        reset_in = 60 - (now % 60)

        return RateLimitResult(
            allowed=count <= self.per_minute,
            remaining=remaining,
            limit=self.per_minute,
            reset_in_seconds=reset_in,
        )


class RedisCircuitBreaker:
    """
    Redis-backed circuit breaker per tool.
    """

    def __init__(
        self,
        r: redis.Redis,
        fail_threshold: int,
        window_seconds: int,
        open_seconds: int,
    ):
        self.r = r
        self.fail_threshold = fail_threshold
        self.window_seconds = window_seconds
        self.open_seconds = open_seconds

    def _k(self, tool: str, suffix: str) -> str:
        return f"cb:{tool}:{suffix}"

    async def allow(self, tool: str) -> tuple[bool, str]:
        state = await self.r.get(self._k(tool, "state")) or "closed"

        if state == "open":
            open_until = int(await self.r.get(self._k(tool, "open_until")) or "0")
            if int(time.time()) >= open_until:
                await self.r.set(self._k(tool, "state"), "half_open", ex=self.open_seconds)
                await self.r.set(self._k(tool, "trial"), "0", ex=self.open_seconds)
                return True, "half_open"
            return False, "open"

        if state == "half_open":
            trial = await self.r.get(self._k(tool, "trial")) or "0"
            if trial == "1":
                return False, "half_open"
            await self.r.set(self._k(tool, "trial"), "1", ex=self.open_seconds)
            return True, "half_open"

        return True, "closed"

    async def on_success(self, tool: str) -> None:
        await self.r.set(self._k(tool, "state"), "closed", ex=self.window_seconds)
        await self.r.delete(self._k(tool, "fail_count"))

    async def on_failure(self, tool: str) -> None:
        state = await self.r.get(self._k(tool, "state")) or "closed"
        now = int(time.time())

        if state == "half_open":
            await self._open(tool, now)
            return

        count = await self.r.incr(self._k(tool, "fail_count"))
        if count == 1:
            await self.r.expire(self._k(tool, "fail_count"), self.window_seconds)

        if count >= self.fail_threshold:
            await self._open(tool, now)

    async def _open(self, tool: str, now: int) -> None:
        await self.r.set(self._k(tool, "state"), "open", ex=self.open_seconds)
        await self.r.set(self._k(tool, "open_until"), now + self.open_seconds, ex=self.open_seconds)
