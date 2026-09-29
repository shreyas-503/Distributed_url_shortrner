import pytest

from app.utils.base62 import (
    decode_base62,
    encode_base62,
)


def test_encode_zero():
    assert encode_base62(0) == "0"


def test_encode_single_values():
    assert encode_base62(1) == "1"
    assert encode_base62(10) == "a"
    assert encode_base62(35) == "z"
    assert encode_base62(36) == "A"
    assert encode_base62(61) == "Z"


def test_base62_round_trip():
    values = [
        0,
        1,
        10,
        61,
        62,
        100,
        1000,
        123456,
        999999,
        999999999,
    ]

    for value in values:
        encoded = encode_base62(value)
        decoded = decode_base62(encoded)

        assert decoded == value


def test_encode_negative_number():
    with pytest.raises(ValueError):
        encode_base62(-1)


def test_decode_invalid_character():
    with pytest.raises(ValueError):
        decode_base62("@")