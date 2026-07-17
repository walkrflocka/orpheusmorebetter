import pytest

from services import tagging

@pytest.mark.parametrize(
    "value,expected",
    [
        ("1", True),
        ("A", False),
        ("01", True),
        ("A1", True),
        ("1A", False),
        ("AA1", False),
        ("A01", True),
        ("1/12", True),
        ("A/12", False),
        ("01/12", True),
        ("A1/12", True),
        ("a1/12", True),
        ("1A/12", False),
        ("Z9/10", True),
        ("B02/03", True),
        ("AA1/12", False),
    ],
)
def test_valid_fractional_tag(value, expected):
    assert tagging.valid_fractional_tag(value) is expected