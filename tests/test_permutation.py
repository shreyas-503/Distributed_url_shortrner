import pytest

from app.utils.base62 import encode_short_code
from app.utils.permutation import permute_id

from app.utils.permutation import (
    permute_id,
    unpermute_id,
)

from app.utils.base62 import (
    decode_base62,
    encode_base62,
)


def test_permutation_is_deterministic():
    value = 123456

    assert permute_id(value) == permute_id(value)


@pytest.mark.parametrize(
    "value",
    [
        0,
        1,
        2,
        42,
        1000,
        123456,
        999999999,],
)
def test_permutation_round_trip(
    value: int,
):
    permuted = permute_id(value)

    assert unpermute_id(permuted) == value


def test_sequential_ids_are_not_sequential():
    first = permute_id(100)
    second = permute_id(101)

    assert second != first + 1


def test_negative_value_rejected():
    with pytest.raises(ValueError):
        permute_id(-1)

    with pytest.raises(ValueError):
        unpermute_id(-1)


def test_permuted_values_are_unique():
    values = range(1000)

    permuted_values = {
        permute_id(value)
        for value in values
    }

    assert len(permuted_values) == 1000


@pytest.mark.parametrize(
    "value",
    [
        1,
        42,
        123,
        999999,
    ],
)
def test_short_code_round_trip(
    value: int,
):
    short_code = encode_base62(
        permute_id(value)
    )

    restored_value = unpermute_id(
        decode_base62(short_code)
    )

    assert restored_value == value