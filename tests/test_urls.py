from collections.abc import AsyncGenerator, Generator
from datetime import datetime, timedelta, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.main import app
from tests.conftest import TestingSessionLocal


@pytest.fixture()
def db() -> Generator[Session, None, None]:
    database = TestingSessionLocal()

    try:
        yield database
    finally:
        database.close()


@pytest.fixture()
async def client(
    db: Session,
) -> AsyncGenerator[AsyncClient, None]:

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as test_client:
        yield test_client

    app.dependency_overrides.clear()


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
async def test_unknown_short_code_returns_404(
    client: AsyncClient,
):
    response = await client.get(
        "/api/v1/urls/does-not-exist",
    )

    assert response.status_code == 404

    assert response.json() == {
        "detail": "URL not found"
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
async def test_expired_url_returns_404(
    client: AsyncClient,
):
    expires_at = (
        datetime.now(timezone.utc)
        - timedelta(minutes=5)
    )

    create_response = await client.post(
        "/api/v1/urls",
        json={
            "url": "https://example.com",
            "expires_at": expires_at.isoformat(),
        },
    )

    assert create_response.status_code == 201

    short_code = create_response.json()["short_code"]

    response = await client.get(
        f"/{short_code}",
        follow_redirects=False,
    )

    assert response.status_code == 404

    assert response.json() == {
        "detail": "Short URL has expired"
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