import pytest
from httpx import AsyncClient

from app.cache.cache_service import check_bloom_filter

@pytest.mark.anyio
async def test_bloom_filter_blocks_nonexistent_urls(client: AsyncClient):
    """
    Prove that a random, un-created short code gets blocked
    by the Bloom filter before hitting the database.
    """
    fake_short_code = "zzzzzzz"
    
    # 1. Check the bloom filter directly
    might_exist = await check_bloom_filter(fake_short_code)
    assert might_exist is False, "Bloom filter should return False for non-existent code"

    # 2. Check via the API (should return 404 instantly without DB query)
    response = await client.get(f"/{fake_short_code}", follow_redirects=False)
    assert response.status_code == 404

@pytest.mark.anyio
async def test_bloom_filter_allows_created_urls(client: AsyncClient):
    """
    Prove that when a URL is created, it is added to the Bloom filter
    and successfully passes the check.
    """
    # 1. Create a URL
    create_response = await client.post(
        "/api/v1/urls",
        json={"url": "https://distributed-test.com"},
    )
    assert create_response.status_code == 201
    
    short_code = create_response.json()["short_code"]

    # 2. Check the bloom filter directly
    might_exist = await check_bloom_filter(short_code)
    assert might_exist is True, "Bloom filter should return True for created code"

    # 3. Check via the API (should return 307 Redirect)
    response = await client.get(f"/{short_code}", follow_redirects=False)
    assert response.status_code == 307