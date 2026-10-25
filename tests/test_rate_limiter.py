from unittest.mock import Mock

import pytest
from fastapi import HTTPException
from redis.exceptions import RedisError
from starlette.requests import Request

from app.core import rate_limiter

from unittest.mock import AsyncMock, Mock
import pytest


def create_request(
    client_ip: str = "127.0.0.1",
) -> Request:
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/v1/urls",
        "headers": [],
        "client": (
            client_ip,
            12345,
        ),
    }

    return Request(scope)


async def test_rate_limiter_allows_request_under_limit(monkeypatch):
    redis_eval = AsyncMock(return_value=1)
    monkeypatch.setattr(rate_limiter.redis_client, "eval", redis_eval)
    
    request = create_request()
    await rate_limiter.rate_limit(request)

    redis_eval.assert_called_once_with(
        rate_limiter.RATE_LIMIT_SCRIPT,
        1,
        "rate_limit:127.0.0.1",
        rate_limiter.RATE_LIMIT_WINDOW,
    )

'''
def test_rate_limiter_rejects_request_over_limit(
    monkeypatch,
):
    monkeypatch.setattr(
        rate_limiter.redis_client,
        "eval",
        Mock(
            return_value=(
                rate_limiter.RATE_LIMIT + 1
            ),
        ),
    )

    request = create_request()

    with pytest.raises(
        HTTPException,
    ) as exception:

        rate_limiter.rate_limit(
            request,
        )

    assert (
        exception.value.status_code
        == 429
    )

def test_rate_limiter_fails_open_when_redis_fails(
    monkeypatch,
):
    def raise_redis_error(
        *args,
        **kwargs,
    ):
        raise RedisError(
            "Redis unavailable"
        )

    monkeypatch.setattr(
        rate_limiter.redis_client,
        "eval",
        raise_redis_error,
    )

    request = create_request()

    rate_limiter.rate_limit(
        request,
    )
'''

@pytest.mark.anyio
async def test_rate_limiter_rejects_request_over_limit(monkeypatch):
    monkeypatch.setattr(rate_limiter.redis_client, "eval", AsyncMock(return_value=rate_limiter.RATE_LIMIT + 1))
    
    request = create_request()
    with pytest.raises(HTTPException) as exception:
        await rate_limiter.rate_limit(request)
    assert exception.value.status_code == 429

@pytest.mark.anyio
async def test_rate_limiter_fails_open_when_redis_fails(monkeypatch):
    async def raise_redis_error(*args, **kwargs):
        raise RedisError("Redis unavailable")

    monkeypatch.setattr(rate_limiter.redis_client, "eval", raise_redis_error)
    request = create_request()
    await rate_limiter.rate_limit(request)