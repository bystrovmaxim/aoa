# tests/intents/logging/test_masking_edges.py
"""mask_value branches for full-length strings and coerced config."""

from __future__ import annotations

from action_machine.logging.masking import mask_value


def test_mask_value_returns_original_when_keep_covers_full_string() -> None:
    assert mask_value("ab", {"max_chars": 10, "max_percent": 100}) == "ab"


def test_mask_value_coerces_non_int_max_chars_to_default() -> None:
    out = mask_value("secret", {"max_chars": "bad", "max_percent": 1})
    assert out != "secret"
    assert "*" in out


def test_mask_value_coerces_non_str_char_to_default() -> None:
    out = mask_value("secret", {"max_chars": 1, "char": 99, "max_percent": 1})
    assert out.endswith("*****")


def test_mask_value_coerces_non_int_max_percent_to_default() -> None:
    out = mask_value("abcdefghij", {"max_chars": 2, "max_percent": "x"})
    assert out != "abcdefghij"
