import hashlib
import hmac

from app.core.config import settings


BASE = 62
SHORT_CODE_LENGTH = 7

DOMAIN_SIZE = BASE ** SHORT_CODE_LENGTH

HALF_BITS = 21
HALF_MASK = (1 << HALF_BITS) - 1

ROUNDS = 6


def _round_function(
    value: int,
    round_number: int,
) -> int:
    """
    Generate a keyed pseudo-random value
    for one Feistel round.
    """

    message = (
        f"{round_number}:{value}"
    ).encode()

    digest = hmac.new(
        settings.short_code_secret.encode(),
        message,
        hashlib.sha256,
    ).digest()

    return (
        int.from_bytes(
            digest[:4],
            byteorder="big",
        )
        & HALF_MASK
    )


def _permute_42bit(
    value: int,
) -> int:
    """
    Permute a value inside a 42-bit space.
    """

    left = (
        value >> HALF_BITS
    ) & HALF_MASK

    right = (
        value & HALF_MASK
    )

    for round_number in range(ROUNDS):

        left, right = (
            right,
            (
                left
                ^ _round_function(
                    right,
                    round_number,
                )
            )
            & HALF_MASK,
        )

    return (
        left << HALF_BITS
    ) | right


def _unpermute_42bit(
    value: int,
) -> int:
    """
    Reverse the 42-bit Feistel permutation.
    """

    left = (
        value >> HALF_BITS
    ) & HALF_MASK

    right = (
        value & HALF_MASK
    )

    for round_number in reversed(
        range(ROUNDS)
    ):

        left, right = (
            (
                right
                ^ _round_function(
                    left,
                    round_number,
                )
            )
            & HALF_MASK,
            left,
        )

    return (
        left << HALF_BITS
    ) | right


def permute_id(
    value: int,
) -> int:
    """
    Permute a PostgreSQL ID into the
    fixed 7-character Base62 domain.

    Cycle walking guarantees:

        0 <= result < 62^7
    """

    if value < 0:
        raise ValueError(
            "Value must be non-negative"
        )

    if value >= DOMAIN_SIZE:
        raise ValueError(
            "Value exceeds 7-character domain"
        )

    result = _permute_42bit(
        value
    )

    while result >= DOMAIN_SIZE:

        result = _permute_42bit(
            result
        )

    return result


def unpermute_id(
    value: int,
) -> int:
    """
    Reverse the fixed-domain permutation.
    """

    if value < 0:
        raise ValueError(
            "Value must be non-negative"
        )

    if value >= DOMAIN_SIZE:
        raise ValueError(
            "Value exceeds 7-character domain"
        )

    result = _unpermute_42bit(
        value
    )

    while result >= DOMAIN_SIZE:

        result = _unpermute_42bit(
            result
        )

    return result