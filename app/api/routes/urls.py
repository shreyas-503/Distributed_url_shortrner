from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy.orm import Session

from app.core.rate_limiter import rate_limit
from app.db.database import get_db
from app.schemas.url import (
    URLCreate,
    URLInfoResponse,
    URLResponse,
)
from app.services.url_service import (
    create_short_url,
    deactivate_url,
    get_url_by_code,
    is_url_expired,
)


router = APIRouter(
    prefix="/api/v1/urls",
    tags=["URLs"],
)


@router.post(
    "",
    response_model=URLResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_url(
    payload: URLCreate,
    db: Session = Depends(get_db),
    _: None = Depends(rate_limit),
):
    url = create_short_url(
        db=db,
        original_url=str(payload.url),
        expires_at=payload.expires_at,
    )

    return URLResponse(
        short_code=url.short_code,
        short_url=f"http://localhost:8000/{url.short_code}",
        original_url=url.original_url,
        created_at=url.created_at,
        expires_at=url.expires_at,
        is_active=url.is_active,
    )


@router.get(
    "/{short_code}",
    response_model=URLInfoResponse,
)
def get_url_info(
    short_code: str,
    db: Session = Depends(get_db),
):
    url = get_url_by_code(
        db=db,
        short_code=short_code,
    )

    if url is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="URL not found",
        )

    if is_url_expired(url):
        deactivate_url(
            db=db,
            url=url,
        )

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="URL has expired",
        )

    return URLInfoResponse(
        short_code=url.short_code,
        original_url=url.original_url,
        created_at=url.created_at,
        expires_at=url.expires_at,
        is_active=url.is_active,
    )


@router.delete(
    "/{short_code}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_url(
    short_code: str,
    db: Session = Depends(get_db),
):
    url = get_url_by_code(
        db=db,
        short_code=short_code,
    )

    if url is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="URL not found",
        )

    deactivate_url(
        db=db,
        url=url,
    )

    return None