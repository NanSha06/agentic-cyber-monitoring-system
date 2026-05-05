"""
Redis pub/sub wrapper for V3 agent events.

The in-memory fallback keeps local tests and demos usable when Redis is not
running. Production deployments should set REDIS_URL and use Redis.
"""
from __future__ import annotations

import json
import os
from collections import defaultdict
from typing import Any

from agents.base import AgentInput, AgentOutput


class InMemoryEventBus:
    def __init__(self) -> None:
        self.messages: dict[str, list[dict[str, Any]]] = defaultdict(list)

    async def publish(self, channel: str, message: dict[str, Any]) -> None:
        self.messages[channel].append(message)

    async def publish_input(self, agent_name: str, message: AgentInput) -> None:
        await self.publish(f"agents.{agent_name}.input", message.model_dump(mode="json"))

    async def publish_output(self, message: AgentOutput) -> None:
        await self.publish("agents.output", message.model_dump(mode="json"))

    async def publish_dead_letter(self, message: dict[str, Any]) -> None:
        await self.publish("agents.dead_letter", message)

    async def close(self) -> None:
        return None


class RedisEventBus:
    def __init__(self, redis_url: str) -> None:
        try:
            import redis.asyncio as redis
        except ModuleNotFoundError as exc:
            raise RuntimeError("redis package is not installed") from exc

        self.redis_url = redis_url
        self.client = redis.from_url(redis_url, decode_responses=True)

    async def publish(self, channel: str, message: dict[str, Any]) -> None:
        await self.client.publish(channel, json.dumps(message, default=str))

    async def publish_input(self, agent_name: str, message: AgentInput) -> None:
        await self.publish(f"agents.{agent_name}.input", message.model_dump(mode="json"))

    async def publish_output(self, message: AgentOutput) -> None:
        await self.publish("agents.output", message.model_dump(mode="json"))

    async def publish_dead_letter(self, message: dict[str, Any]) -> None:
        await self.publish("agents.dead_letter", message)

    async def close(self) -> None:
        await self.client.aclose()


async def create_event_bus() -> RedisEventBus | InMemoryEventBus:
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        return InMemoryEventBus()

    try:
        bus = RedisEventBus(redis_url)
    except RuntimeError:
        return InMemoryEventBus()
    try:
        await bus.client.ping()
    except Exception:
        await bus.close()
        return InMemoryEventBus()
    return bus
