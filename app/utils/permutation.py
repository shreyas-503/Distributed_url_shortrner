import hashlib
import hmac
from app.core.config import settings

BASE = 62
SHORT_CODE_LENGTH = 8

DOMAIN_SIZE = BASE ** SHORT_CODE_LENGTH

HALF_BITS = 24
HALF_MASK = (1 << HALF_BITS) - 1
ROUNDS = 6

def _round_function(value: int, round_number: int) -> int:
    message = f"{round_number}:{value}".encode()
    digest = hmac.new(settings.short_code_secret.encode(), message, hashlib.sha256).digest()
    return int.from_bytes(digest[:4], byteorder="big") & HALF_MASK

def _permute_48bit(value: int) -> int:
    left = (value >> HALF_BITS) & HALF_MASK
    right = value & HALF_MASK
    for round_number in range(ROUNDS):
        left, right = right, (left ^ _round_function(right, round_number)) & HALF_MASK
    return (left << HALF_BITS) | right

def _unpermute_48bit(value: int) -> int:
    left = (value >> HALF_BITS) & HALF_MASK
    right = value & HALF_MASK
    for round_number in reversed(range(ROUNDS)):
        left, right = (right ^ _round_function(left, round_number)) & HALF_MASK, left
    return (left << HALF_BITS) | right

def permute_id(value: int) -> int:
    if value < 0 or value >= DOMAIN_SIZE:
        raise ValueError("Value out of bounds")
    result = _permute_48bit(value)
    while result >= DOMAIN_SIZE:
        result = _permute_48bit(result)
    return result

def unpermute_id(value: int) -> int:
    if value < 0 or value >= DOMAIN_SIZE:
        raise ValueError("Value out of bounds")
    result = _unpermute_48bit(value)
    while result >= DOMAIN_SIZE:
        result = _unpermute_48bit(result)
    return result