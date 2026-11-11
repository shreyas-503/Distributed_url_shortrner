'''from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.services.lookup_result import URLLookupStatus
from app.services.url_service import get_url_for_redirect


router = APIRouter(
    tags=["Redirect"],
)


@router.get("/{short_code}")
async def redirect_url(short_code: str, db: AsyncSession = Depends(get_db)):
    result = await get_url_for_redirect(db=db, short_code=short_code)

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
    )'''
from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.services.lookup_result import URLLookupStatus
from app.services.url_service import get_url_for_redirect
from app.cache.cache_service import log_click_to_stream 

# Initialize the router (This was accidentally commented out!)
router = APIRouter(
    tags=["Redirect"],
)

@router.get("/{short_code}")
async def redirect_url(
    short_code: str,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    result = await get_url_for_redirect(db=db, short_code=short_code)

    if result.status == URLLookupStatus.NOT_FOUND:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Short URL not found"
        )
        
    if result.status == URLLookupStatus.EXPIRED:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Short URL has expired"
        )

    # Get user details for analytics
    ip_address = request.headers.get("X-Forwarded-For", request.client.host if request.client else "Unknown")
    user_agent = request.headers.get("user-agent", "Unknown")

    # Fire and forget: push to Redis Stream WITHOUT slowing down the redirect
    background_tasks.add_task(log_click_to_stream, short_code, ip_address, user_agent)

    return RedirectResponse(
        url=result.original_url,
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    )