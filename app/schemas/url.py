from datetime import datetime

from pydantic import BaseModel, HttpUrl


class URLCreate(BaseModel):
    url: HttpUrl
    expires_at: datetime | None = None


class URLResponse(BaseModel):
    short_code: str
    short_url: str
    original_url: str
    created_at: datetime
    expires_at: datetime | None
    is_active: bool

    model_config = {
        "from_attributes": True
    }


class URLInfoResponse(BaseModel):
    short_code: str
    original_url: str
    created_at: datetime
    expires_at: datetime | None
    is_active: bool

    model_config = {
        "from_attributes": True
    }