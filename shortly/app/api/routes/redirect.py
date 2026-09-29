from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services.lookup_result import URLLookupStatus
from app.services.url_service import get_url_for_redirect


router = APIRouter(
    tags=["Redirect"],
)


@router.get("/{short_code}")
def redirect_url(
    short_code: str,
    db: Session = Depends(get_db),
):
    result = get_url_for_redirect(
        db=db,
        short_code=short_code,
    )

    if result.status == URLLookupStatus.NOT_FOUND:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Short URL not found",
        )

    if result.status == URLLookupStatus.EXPIRED:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Short URL has expired",
        )

    return RedirectResponse(
        url=result.original_url,
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    )