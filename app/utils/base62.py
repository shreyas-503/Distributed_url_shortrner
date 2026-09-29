ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
BASE = len(ALPHABET)


SHORT_CODE_LENGTH = 7


def encode_short_code(
    value: int,
) -> str:
    """
    Encode an integer as an exactly
    7-character Base62 short code.
    """

    encoded = encode_base62(
        value
    )

    if len(encoded) > SHORT_CODE_LENGTH:
        raise ValueError(
            "Value exceeds short code length"
        )

    return encoded.rjust(
        SHORT_CODE_LENGTH,
        "0",
    )


def decode_short_code(
    short_code: str,
) -> int:
    """
    Decode an exactly 7-character
    Base62 short code.
    """

    if len(short_code) != SHORT_CODE_LENGTH:
        raise ValueError(
            "Short code must be exactly "
            f"{SHORT_CODE_LENGTH} characters"
        )

    return decode_base62(
        short_code
    )

def encode_base62(number: int) -> str:
    if number < 0:
        raise ValueError("number must be non-negative")

    if number == 0:
        return ALPHABET[0]

    result = []

    while number:
        number, remainder = divmod(number, BASE)
        result.append(ALPHABET[remainder])

    return "".join(reversed(result))


def decode_base62(value: str) -> int:
    number = 0

    for char in value:
        if char not in ALPHABET:
            raise ValueError(f"Invalid Base62 character: {char}")

        number = number * BASE + ALPHABET.index(char)

    return number