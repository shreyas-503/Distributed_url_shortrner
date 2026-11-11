import os
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock  # <-- Add this

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool  # <-- Add this

from app.db.database import Base, get_db
from app.main import app


import sys
import asyncio

import redis.asyncio as redis
from app.cache import cache_service
from app.core import rate_limiter
from app.core.config import settings

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://shortly:shortly_password@localhost:5432/shortly"
)

# FIX 1: Add NullPool to prevent Event Loop crossover errors
engine = create_async_engine(
    TEST_DATABASE_URL,
    poolclass=NullPool,  
)

TestingSessionLocal = async_sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    class_=AsyncSession,
)

@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"

@pytest.fixture(scope="session", autouse=True)
async def setup_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

# FIX 2: Mock the background task so it doesn't leave pending tasks when tests exit
@pytest.fixture(autouse=True)
def mock_background_tasks(monkeypatch):
    monkeypatch.setattr(
        "app.api.routes.redirect.log_click_to_stream", 
        AsyncMock()
    )

@pytest.fixture()
async def db() -> AsyncGenerator[AsyncSession, None]:
    async with TestingSessionLocal() as session:
        yield session

@pytest.fixture()
async def client(
    db: AsyncSession,
) -> AsyncGenerator[AsyncClient, None]:

    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(
        app=app,
        client=("127.0.0.1", 12345),
    )

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as async_client:
        yield async_client

    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
async def setup_redis(monkeypatch):
    """
    Provide a fresh Redis client for every test.
    This prevents 'Event loop is closed' errors by ensuring
    the Redis connection pool is bound to the current test's loop.
    """
    client = redis.Redis.from_url(
        settings.redis_url,
        decode_responses=True,
    )
    
    # Swap out the global client in the modules that use it
    monkeypatch.setattr(cache_service, "redis_client", client)
    monkeypatch.setattr(rate_limiter, "redis_client", client)
    
    # Flush the cache so previous tests don't pollute the current one
    await client.flushdb()
    
    yield client
    
    # Safely close the connections when the test finishes
    await client.aclose()