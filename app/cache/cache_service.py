import json
from datetime import datetime, timezone

from redis.exceptions import RedisError
from app.cache.redis_client import redis_client

CACHE_TTL_SECONDS = 3600

def get_cache_key(short_code: str) -> str:
    return f"url:{short_code}"

def get_cache_ttl(expires_at: str | None) -> int | None:
    if expires_at is None:
        return CACHE_TTL_SECONDS

    expiration_time = datetime.fromisoformat(expires_at)
    remaining_seconds = int((expiration_time - datetime.now(timezone.utc)).total_seconds())

    if remaining_seconds <= 0:
        return None

    return min(CACHE_TTL_SECONDS, remaining_seconds)

async def cache_url(short_code: str, original_url: str, expires_at: str | None) -> None:
    cache_key = get_cache_key(short_code=short_code)
    ttl = get_cache_ttl(expires_at=expires_at)

    if ttl is None:
        return

    data = {"original_url": original_url, "expires_at": expires_at}
    try:
        await redis_client.set(cache_key, json.dumps(data), ex=ttl)
    except RedisError:
        return

async def get_cached_url(short_code: str) -> dict | None:
    cache_key = get_cache_key(short_code=short_code)
    try:
        cached_data = await redis_client.get(cache_key)
    except RedisError:
        return None

    if cached_data is None:
        return None

    return json.loads(cached_data)

async def delete_cached_url(short_code: str) -> None:
    try:
        await redis_client.delete(get_cache_key(short_code=short_code))
    except RedisError:
        return

BLOOM_FILTER_KEY = "shortly:bf"

async def initialize_bloom_filter():
    """
    Ensure the Bloom filter exists.
    Called on app startup.
    error_rate=0.01 (1% false positive rate)
    capacity=10,000,000 (Expected number of URLs)
    """
    try:
        # Check if it exists to avoid recreation errors
        await redis_client.bf().info(BLOOM_FILTER_KEY)
    except RedisError:
        try:
            await redis_client.bf().reserve(BLOOM_FILTER_KEY, 0.01, 10000000)
        except RedisError:
            pass

async def add_to_bloom_filter(short_code: str) -> None:
    """Add a new short code to the Bloom filter."""
    try:
        await redis_client.bf().add(BLOOM_FILTER_KEY, short_code)
    except RedisError:
        pass

async def check_bloom_filter(short_code: str) -> bool:
    """
    Check if a short code might exist.
    Returns False if it DEFINITELY DOES NOT exist.
    Returns True if it PROBABLY exists (or if Redis fails, to fail open).
    """
    try:
        return await redis_client.bf().exists(BLOOM_FILTER_KEY, short_code)
    except RedisError:
        return True  


async def log_click_to_stream(short_code: str, ip_address: str, user_agent: str) -> None:
    """
    Publish a click event to a Redis Stream for asynchronous analytics processing.
    """
    try:
        event_data = {
            "short_code": short_code,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        # XADD command adds the entry to the stream named "clicks:stream"
        await redis_client.xadd("clicks:stream", event_data)
    except RedisError:
        pass