import pytest
from httpx import AsyncClient

from app.cache.redis_client import redis_client
from app.core.rate_limiter import (
    RATE_LIMIT,
)


@pytest.mark.anyio
async def test_rate_limit(
    client: AsyncClient,
):
    client_ip = "127.0.0.1"

    key = (
        f"rate_limit:{client_ip}"
    )

    # Ensure previous test runs do not
    # affect this test.
    redis_client.delete(key)

    try:
        for _ in range(RATE_LIMIT):
            response = await client.post(
                "/api/v1/urls",
                json={
                    "url": "https://example.com",
                },
            )

            assert response.status_code == 201

        response = await client.post(
            "/api/v1/urls",
            json={
                "url": "https://example.com",
            },
        )

        assert response.status_code == 429

        assert response.json() == {
            "detail": (
                "Rate limit exceeded. "
                "Try again later."
            )
        }

    finally:
        # Cleanup Redis after the test.
        redis_client.delete(key)