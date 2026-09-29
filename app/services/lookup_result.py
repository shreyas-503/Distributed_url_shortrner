from dataclasses import dataclass
from enum import Enum


class URLLookupStatus(str, Enum):
    FOUND = "found"
    NOT_FOUND = "not_found"
    EXPIRED = "expired"


@dataclass
class URLLookupResult:
    status: URLLookupStatus
    original_url: str | None = None