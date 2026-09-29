from datetime import datetime, timezone

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

import secrets


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
    """

    url.is_active = False

    db.commit()
    db.refresh(url)


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