"""Short-lived revenue cache, isolated by tenant and property."""

import json
import os
from typing import Any

import redis.asyncio as redis

from app.services.reservations import calculate_total_revenue

redis_client = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))


async def get_revenue_summary(property_id: str, tenant_id: str, month: int, year: int) -> dict[str, Any]:
    cache_key = f"revenue:v3:{tenant_id}:{property_id}:{year}:{month}"
    try:
        cached = await redis_client.get(cache_key)
        if cached:
            return json.loads(cached)
    except redis.RedisError:
        pass

    result = await calculate_total_revenue(property_id, tenant_id, month, year)
    try:
        await redis_client.setex(cache_key, 300, json.dumps(result))
    except redis.RedisError:
        pass
    return result
