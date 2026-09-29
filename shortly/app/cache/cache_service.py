import json

from app.cache.redis_client import redis_client


CACHE_TTL_SECONDS = 3600


def get_cache_key(
    short_code: str,
) -> str:
    return f"url:{short_code}"


def cache_url(
    short_code: str,
    original_url: str,
    expires_at: str | None,
) -> None:
    cache_key = get_cache_key(
        short_code=short_code,
    )

    data = {
        "original_url": original_url,
        "expires_at": expires_at,
    }

    redis_client.set(
        cache_key,
        json.dumps(data),
        ex=CACHE_TTL_SECONDS,
    )


def get_cached_url(
    short_code: str,
) -> dict | None:
    cache_key = get_cache_key(
        short_code=short_code,
    )

    cached_data = redis_client.get(
        cache_key,
    )

    if cached_data is None:
        return None

    return json.loads(cached_data)


def delete_cached_url(
    short_code: str,
) -> None:
    cache_key = get_cache_key(
        short_code=short_code,
    )

    redis_client.delete(
        cache_key,
    )