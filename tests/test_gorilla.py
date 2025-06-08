from hypothesis import strategies as st, given
from numpy.testing import assert_equal

from python_gorilla import encode, decode


@given(st.lists(st.floats()))
def test_encode_decode(input: list[float]) -> None:
    # We use numpy's assert_equal so that NaN == NaN
    assert_equal(decode(encode(input)), input)
