import pytest

from app.utils.base62 import (
    decode_short_code,
    encode_short_code,
)
from app.utils.permutation import (
    permute_id,
    unpermute_id,
)


def test_permutation_is_deterministic():
    value = 123456

    first_result = permute_id(
        value
    )

    second_result = permute_id(
        value
    )

    assert first_result == second_result


@pytest.mark.parametrize(
    "value",
    [
        0,
        1,
        2,
        42,
        1000,
        123456,
        999999999,
    ],
)
def test_permutation_round_trip(
    value: int,
):
    permuted_value = permute_id(
        value
    )

    restored_value = unpermute_id(
        permuted_value
    )

    assert restored_value == value


def test_sequential_ids_are_not_sequential():
    first = permute_id(100)

    second = permute_id(101)

    third = permute_id(102)

    assert first != 100
    assert second != 101
    assert third != 102

    assert second - first != 1
    assert third - second != 1


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
    permuted_value = permute_id(
        value
    )

    short_code = encode_short_code(
        permuted_value
    )

    decoded_value = decode_short_code(
        short_code
    )

    restored_value = unpermute_id(
        decoded_value
    )

    assert restored_value == value


def test_short_code_is_always_seven_characters():
    test_values = [
        0,
        1,
        42,
        123,
        999999,
        1000000000,
    ]

    for value in test_values:

        permuted_value = permute_id(
            value
        )

        short_code = encode_short_code(
            permuted_value
        )

        assert len(short_code) == 7


def test_fixed_length_short_code_round_trip():
    original_value = 123456

    permuted_value = permute_id(
        original_value
    )

    short_code = encode_short_code(
        permuted_value
    )

    decoded_value = decode_short_code(
        short_code
    )

    restored_value = unpermute_id(
        decoded_value
    )

    assert restored_value == original_value
    assert len(short_code) == 7


def test_short_code_rejects_invalid_length():
    with pytest.raises(ValueError):
        decode_short_code("abc")

    with pytest.raises(ValueError):
        decode_short_code("abcdefgh")