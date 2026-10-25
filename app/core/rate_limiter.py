from fastapi import HTTPException, Request, status
from redis.exceptions import RedisError

from app.cache.redis_client import redis_client


RATE_LIMIT = 100
RATE_LIMIT_WINDOW = 60


RATE_LIMIT_SCRIPT = """
local current = redis.call(
    "INCR",
    KEYS[1]
)

if current == 1 then
    redis.call(
        "EXPIRE",
        KEYS[1],
        ARGV[1]
    )
end

return current
"""



async def rate_limit(request: Request) -> None:

    """
    Limit URL creation requests per client IP.

    Policy:
        100 requests per 60 seconds.

    Uses an atomic Redis Lua script to ensure
    the counter and expiration are set safely.
    """

    if request.client is None:
        return

    client_ip = request.headers.get("X-Forwarded-For", request.client.host)
    key = f"rate_limit:{client_ip}"

    try:
        current_requests = await redis_client.eval(
            RATE_LIMIT_SCRIPT, 1, key, RATE_LIMIT_WINDOW
        )
    except RedisError:
        return

    if current_requests > RATE_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Try again later.",
        )