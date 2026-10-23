"""Headless validation tests for the optional desktop interface."""

import pytest

from openwave.gui import validate_inputs


def test_gui_accepts_wr90_defaults():
    assert validate_inputs("22.86", "10.16", "4") == (22.86, 10.16, 4)


@pytest.mark.parametrize(
    ("width", "height", "count"),
    [
        ("0", "10", "4"),
        ("-1", "10", "4"),
        ("nan", "10", "4"),
        ("22", "inf", "4"),
        ("bad", "10", "4"),
        ("22", "10", "0"),
        ("22", "10", "13"),
        ("22", "10", "2.5"),
    ],
)
def test_gui_rejects_bad_inputs(width, height, count):
    with pytest.raises(ValueError):
        validate_inputs(width, height, count)
