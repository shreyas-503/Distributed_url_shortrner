from fastapi import HTTPException, Request, status

from app.cache.redis_client import redis_client


RATE_LIMIT = 100
RATE_LIMIT_WINDOW = 60


def rate_limit(
    request: Request,
) -> None:
    """
    Limit URL creation requests per client IP.

    Policy:
        100 requests per 60 seconds.
    """

    client_ip = request.client.host

    #print(request.client.host)

    key = (
        f"rate_limit:{client_ip}"
    )

    current_requests = redis_client.incr(
        key
    )

    if current_requests == 1:
        redis_client.expire(
            key,
            RATE_LIMIT_WINDOW,
        )

    if current_requests > RATE_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                "Rate limit exceeded. "
                "Try again later."
            ),
        )