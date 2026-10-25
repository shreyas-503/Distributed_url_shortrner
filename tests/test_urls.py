#from collections.abc import AsyncGenerator, Generator
from datetime import datetime, timedelta, timezone
from httpx import AsyncClient

import pytest
#from httpx import ASGITransport, AsyncClient
from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.main import app
from tests.conftest import TestingSessionLocal

from app.db.models import URL


from fastapi import HTTPException, status

from app.core.rate_limiter import rate_limit

@pytest.mark.anyio
async def test_create_url(
    client: AsyncClient,
):
    response = await client.post(
        "/api/v1/urls",
        json={
            "url": "https://example.com",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert "short_code" in data
    assert data["original_url"] == "https://example.com/"
    assert data["is_active"] is True
    assert data["expires_at"] is None
    assert "created_at" in data


@pytest.mark.anyio
async def test_create_url_rejects_past_expiration(
    client: AsyncClient,
):
    expires_at = (
        datetime.now(timezone.utc)
        - timedelta(minutes=5)
    )

    response = await client.post(
        "/api/v1/urls",
        json={
            "url": "https://example.com",
            "expires_at": expires_at.isoformat(),
        },
    )

    assert response.status_code == 422

    data = response.json()

    assert "expires_at" in str(data)


@pytest.mark.anyio
async def test_get_url_info(
    client: AsyncClient,
):
    create_response = await client.post(
        "/api/v1/urls",
        json={
            "url": "https://example.com",
        },
    )

    assert create_response.status_code == 201

    short_code = create_response.json()["short_code"]

    response = await client.get(
        f"/api/v1/urls/{short_code}",
    )

    assert response.status_code == 200

    data = response.json()

    assert data["short_code"] == short_code
    assert data["original_url"] == "https://example.com/"
    assert data["is_active"] is True


@pytest.mark.anyio
async def test_expired_url_returns_404(
    client: AsyncClient,
    db: AsyncSession,
):
    create_response = await client.post(
        "/api/v1/urls",
        json={
            "url": "https://github.com",
            "expires_at": (
                datetime.now(timezone.utc)
                + timedelta(minutes=5)
            ).isoformat(),
        },
    )

    assert create_response.status_code == 201

    short_code = create_response.json()["short_code"]

    # This MUST be awaited now that the DB is async
    url = await db.scalar(
        select(URL).filter(URL.short_code == short_code)
    )

    assert url is not None

    url.expires_at = (
        datetime.now(timezone.utc)
        - timedelta(minutes=5)
    )

    await db.commit()  # <-- This MUST be awaited

    response = await client.get(
        f"/{short_code}",
        follow_redirects=False,
    )

    assert response.status_code == 404

    assert response.json() == {
        "detail": "Short URL has expired"
    }


@pytest.mark.anyio
async def test_multiple_urls_have_unique_short_codes(
    client: AsyncClient,
):
    first_response = await client.post(
        "/api/v1/urls",
        json={
            "url": "https://example.com",
        },
    )

    second_response = await client.post(
        "/api/v1/urls",
        json={
            "url": "https://python.org",
        },
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201

    first_code = first_response.json()["short_code"]
    second_code = second_response.json()["short_code"]

    assert first_code != second_code


@pytest.mark.anyio
async def test_redirect_to_original_url(
    client: AsyncClient,
):
    create_response = await client.post(
        "/api/v1/urls",
        json={
            "url": "https://example.com",
        },
    )

    assert create_response.status_code == 201

    short_code = create_response.json()["short_code"]

    response = await client.get(
        f"/{short_code}",
        follow_redirects=False,
    )

    assert response.status_code == 307

    assert response.headers["location"] == (
        "https://example.com/"
    )


@pytest.mark.anyio
async def test_delete_url(
    client: AsyncClient,
):
    create_response = await client.post(
        "/api/v1/urls",
        json={
            "url": "https://example.com",
        },
    )

    assert create_response.status_code == 201

    short_code = create_response.json()["short_code"]

    delete_response = await client.delete(
        f"/api/v1/urls/{short_code}",
    )

    assert delete_response.status_code == 204

    get_response = await client.get(
        f"/api/v1/urls/{short_code}",
    )

    assert get_response.status_code == 404

    assert get_response.json() == {
        "detail": "URL not found"
    }


@pytest.mark.anyio
async def test_short_code_is_reversible(
    client: AsyncClient,
):
    create_response = await client.post(
        "/api/v1/urls",
        json={
            "url": "https://example.com",
        },
    )

    assert create_response.status_code == 201

    short_code = create_response.json()[
        "short_code"
    ]

    response = await client.get(
        f"/{short_code}",
        follow_redirects=False,
    )

    assert response.status_code == 307
    assert response.headers["location"] == (
        "https://example.com/"
    )


@pytest.mark.anyio
async def test_deleted_cached_url_cannot_redirect(
    client,
    db,
):
    response = await client.post(
        "/api/v1/urls",
        json={
            "url": "https://example.com/cached-delete",
        },
    )

    assert response.status_code == 201

    data = response.json()
    short_code = data["short_code"]

    # First redirect populates Redis cache.
    response = await client.get(
        f"/{short_code}",
        follow_redirects=False,
    )

    assert response.status_code == 307
    assert response.headers["location"] == (
        "https://example.com/cached-delete"
    )

    # Delete the URL while it is cached.
    response = await client.delete(
        f"/api/v1/urls/{short_code}",
    )

    assert response.status_code == 204

    # The cached value must have been invalidated.
    response = await client.get(
        f"/{short_code}",
        follow_redirects=False,
    )

    assert response.status_code == 404


@pytest.mark.anyio
async def test_create_url_is_rate_limited(
    client: AsyncClient,
):
    def override_rate_limit():
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
        )

    from app.main import app

    app.dependency_overrides[
        rate_limit
    ] = override_rate_limit

    try:
        response = await client.post(
            "/api/v1/urls",
            json={
                "url": "https://example.com",
            },
        )
    finally:
        app.dependency_overrides.pop(
            rate_limit,
            None,
        )

    assert response.status_code == 429

    assert response.json() == {
        "detail": "Rate limit exceeded"
    }