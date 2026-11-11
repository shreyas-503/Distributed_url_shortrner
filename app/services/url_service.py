'''from datetime import datetime, timezone

import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.cache.cache_service import (
    cache_url,
    delete_cached_url,
    get_cached_url,
)
from app.db.models import URL
from app.services.lookup_result import (
    URLLookupResult,
    URLLookupStatus,
)
from app.utils.base62 import (
    decode_short_code,
    encode_short_code,
)
from app.utils.permutation import (
    permute_id,
    unpermute_id,
)


def create_short_url(
    db: Session,
    original_url: str,
    expires_at: datetime | None = None,
) -> URL:
    """
    Create a new shortened URL.

    Flow:

        Temporary short code
                ↓
        PostgreSQL INSERT
                ↓
        Generated ID
                ↓
        Keyed permutation
                ↓
        Base62 encoding
                ↓
        Final short code
    """

    # short_code is VARCHAR(10) NOT NULL.
    # Generate a temporary value that fits the column.
    temporary_short_code = secrets.token_hex(5)

    url = URL(
        original_url=original_url,
        short_code=temporary_short_code,
        expires_at=expires_at,
        is_active=True,
    )

    db.add(url)

    # PostgreSQL INSERT happens here.
    # The generated primary key becomes available.
    db.flush()

    # Obfuscate the sequential database ID.
    permuted_id = permute_id(
        url.id
    )

    # Convert to the final Base62 short code.
    url.short_code = encode_short_code(
        permuted_id
    )

    db.commit()
    db.refresh(url)

    return url


def get_url_by_code(
    db: Session,
    short_code: str,
) -> URL | None:
    """
    Get an active URL using its stored short code.

    Used by:
    - GET /api/v1/urls/{short_code}
    - DELETE /api/v1/urls/{short_code}
    """

    statement = select(URL).where(
        URL.short_code == short_code,
        URL.is_active.is_(True),
    )

    return db.scalar(statement)


def get_url_by_code_any_status(
    db: Session,
    short_code: str,
) -> URL | None:
    """
    Get a URL regardless of its active status.
    """

    statement = select(URL).where(
        URL.short_code == short_code,
    )

    return db.scalar(statement)


def get_url_by_id(
    db: Session,
    url_id: int,
) -> URL | None:
    """
    Get a URL using its PostgreSQL primary key.
    """

    return db.get(
        URL,
        url_id,
    )


def decode_short_code_to_id(
    short_code: str,
) -> int | None:
    """
    Reverse the short-code generation process.
    """

    try:
        permuted_id = decode_short_code(
            short_code
        )

        return unpermute_id(
            permuted_id
        )

    except ValueError:
        return None


def is_url_expired(
    url: URL,
) -> bool:
    """
    Return True if the URL has expired.
    """

    if url.expires_at is None:
        return False

    expires_at = url.expires_at

    # Handle databases that return naive datetimes.
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(
            tzinfo=timezone.utc,
        )

    return expires_at <= datetime.now(
        timezone.utc,
    )


def deactivate_url(
    db: Session,
    url: URL,
) -> None:
    """
    Soft-delete / deactivate a URL.

    Also invalidate the Redis cache so a previously
    cached redirect cannot continue serving a deleted URL.
    """

    url.is_active = False

    db.commit()
    db.refresh(url)

    delete_cached_url(
        short_code=url.short_code,
    )


def get_url_for_redirect(
    db: Session,
    short_code: str,
) -> URLLookupResult:
    """
    Resolve a short code for redirect.

    Flow:

        Short Code
            ↓
        Redis Cache
        /          \
      HIT          MISS
       ↓             ↓
    Return      Base62 Decode
                      ↓
                Reverse Permutation
                      ↓
                 PostgreSQL ID
                      ↓
                  PostgreSQL
    """

    # ----------------------------------------
    # 1. Redis lookup
    # ----------------------------------------

    cached_url = get_cached_url(
        short_code=short_code,
    )

    if cached_url is not None:

        expires_at = cached_url.get(
            "expires_at"
        )

        if expires_at is not None:

            expires_at = datetime.fromisoformat(
                expires_at
            )

            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(
                    tzinfo=timezone.utc,
                )

            if expires_at <= datetime.now(
                timezone.utc,
            ):

                delete_cached_url(
                    short_code=short_code,
                )

                return URLLookupResult(
                    status=URLLookupStatus.EXPIRED,
                )

        return URLLookupResult(
            status=URLLookupStatus.FOUND,
            original_url=cached_url[
                "original_url"
            ],
        )

    # ----------------------------------------
    # 2. Decode short code
    # ----------------------------------------

    url_id = decode_short_code_to_id(
        short_code=short_code,
    )

    if url_id is None:
        return URLLookupResult(
            status=URLLookupStatus.NOT_FOUND,
        )

    # ----------------------------------------
    # 3. PostgreSQL primary-key lookup
    # ----------------------------------------

    url = get_url_by_id(
        db=db,
        url_id=url_id,
    )

    if url is None:
        return URLLookupResult(
            status=URLLookupStatus.NOT_FOUND,
        )

    # ----------------------------------------
    # 4. Active check
    # ----------------------------------------

    if not url.is_active:
        return URLLookupResult(
            status=URLLookupStatus.NOT_FOUND,
        )

    # ----------------------------------------
    # 5. Expiration check
    # ----------------------------------------

    if is_url_expired(url):

        deactivate_url(
            db=db,
            url=url,
        )

        delete_cached_url(
            short_code=short_code,
        )

        return URLLookupResult(
            status=URLLookupStatus.EXPIRED,
        )

    # ----------------------------------------
    # 6. Cache database result
    # ----------------------------------------

    expires_at = None

    if url.expires_at is not None:

        expires_at = url.expires_at.isoformat()

    cache_url(
        short_code=url.short_code,
        original_url=url.original_url,
        expires_at=expires_at,
    )

    # ----------------------------------------
    # 7. Return normalized result
    # ----------------------------------------

    return URLLookupResult(
        status=URLLookupStatus.FOUND,
        original_url=url.original_url,
    )
'''

import secrets
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.cache.cache_service import cache_url, delete_cached_url, get_cached_url,    add_to_bloom_filter, check_bloom_filter
from app.db.models import URL
from app.services.lookup_result import URLLookupResult, URLLookupStatus
from app.utils.base62 import decode_short_code, encode_short_code
from app.utils.permutation import permute_id, unpermute_id
from sqlalchemy import select, text

from sqlalchemy import select, text  

# ... other imports ...

async def create_short_url(
    db: AsyncSession,
    original_url: str,
    expires_at: datetime | None = None,
) -> URL:
    """
    Create a new shortened URL with a SINGLE database insert.
    """
    
    # 1. Ask PostgreSQL for the next ID in the sequence securely.
    # pg_get_serial_sequence ensures we get the exact sequence name 
    # generated by the Identity() column.
    query = text("SELECT nextval(pg_get_serial_sequence('urls', 'id'))")
    result = await db.execute(query)
    next_id = result.scalar()

    # 2. Obfuscate the fetched sequential database ID.
    permuted_id = permute_id(next_id)

    # 3. Convert to the final Base62 short code immediately.
    final_short_code = encode_short_code(permuted_id)

    # 4. Create the URL object with the final data
    url = URL(
        id=next_id,  # <-- We explicitly set the ID here
        original_url=original_url,
        short_code=final_short_code,
        expires_at=expires_at,
        is_active=True,
    )

    # 5. Exactly ONE database write operation
    db.add(url)
    await db.commit()
    await db.refresh(url)

    await add_to_bloom_filter(url.short_code)

    return url

async def get_url_by_code(db: AsyncSession, short_code: str) -> URL | None:
    """Optimized: O(1) Primary Key lookup by reversing the math."""
    url_id = decode_short_code_to_id(short_code)
    if url_id is None:
        return None

    url = await get_url_by_id(db=db, url_id=url_id)
    if url is not None and url.is_active:
        return url
    return None

async def get_url_by_code_any_status(db: AsyncSession, short_code: str) -> URL | None:
    """Optimized: O(1) Primary Key lookup by reversing the math."""
    url_id = decode_short_code_to_id(short_code)
    if url_id is None:
        return None
    return await get_url_by_id(db=db, url_id=url_id)

async def get_url_by_id(db: AsyncSession, url_id: int) -> URL | None:
    return await db.get(URL, url_id)

def decode_short_code_to_id(short_code: str) -> int | None:
    # (Keep existing synchronous code here)
    try:
        return unpermute_id(decode_short_code(short_code))
    except ValueError:
        return None

def is_url_expired(url: URL) -> bool:
    if url.expires_at is None:
        return False
    return url.expires_at <= datetime.now(timezone.utc)

async def deactivate_url(db: AsyncSession, url: URL) -> None:
    url.is_active = False
    await db.commit()
    await db.refresh(url)
    await delete_cached_url(short_code=url.short_code)

async def get_url_for_redirect(db: AsyncSession, short_code: str) -> URLLookupResult:

    might_exist = await check_bloom_filter(short_code)
    if not might_exist:
        return URLLookupResult(status=URLLookupStatus.NOT_FOUND)
    
    cached_url = await get_cached_url(short_code=short_code)
    
    if cached_url is not None:
        expires_at = cached_url.get("expires_at")
        if expires_at is not None:
            if datetime.fromisoformat(expires_at) <= datetime.now(timezone.utc):
                await delete_cached_url(short_code=short_code)
                return URLLookupResult(status=URLLookupStatus.EXPIRED)
        return URLLookupResult(status=URLLookupStatus.FOUND, original_url=cached_url["original_url"])

    url_id = decode_short_code_to_id(short_code=short_code)
    if url_id is None:
        return URLLookupResult(status=URLLookupStatus.NOT_FOUND)

    url = await get_url_by_id(db=db, url_id=url_id)
    if url is None or not url.is_active:
        return URLLookupResult(status=URLLookupStatus.NOT_FOUND)

    if is_url_expired(url):
        await deactivate_url(db=db, url=url)
        return URLLookupResult(status=URLLookupStatus.EXPIRED)

    expires_at_iso = url.expires_at.isoformat() if url.expires_at else None
    await cache_url(short_code=url.short_code, original_url=url.original_url, expires_at=expires_at_iso)

    return URLLookupResult(status=URLLookupStatus.FOUND, original_url=url.original_url)