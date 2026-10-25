from datetime import datetime, timezone

from pydantic import BaseModel, HttpUrl, field_validator


class URLCreate(BaseModel):
    url: HttpUrl
    expires_at: datetime | None = None

    @field_validator("expires_at")
    @classmethod
    def validate_expires_at(
        cls,
        value: datetime | None,
    ) -> datetime | None:
        if value is None:
            return None

        if value.tzinfo is None:
            value = value.replace(
                tzinfo=timezone.utc,
            )

        if value <= datetime.now(timezone.utc):
            raise ValueError(
                "expires_at must be in the future"
            )

        return value


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