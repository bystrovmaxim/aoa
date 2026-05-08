# tests/intents/logging/test_sensitive_decorator_validation.py
"""@sensitive parameter validation and decorator targets."""

from __future__ import annotations

import pytest

from action_machine.intents.sensitive import sensitive


def test_sensitive_rejects_enabled_non_bool() -> None:
    with pytest.raises(TypeError, match="enabled"):
        sensitive(enabled="yes")  # type: ignore[arg-type, call-overload]


def test_sensitive_rejects_max_chars_non_int() -> None:
    with pytest.raises(TypeError, match="max_chars"):
        sensitive(max_chars="3")  # type: ignore[arg-type, call-overload]


def test_sensitive_rejects_negative_max_chars() -> None:
    with pytest.raises(ValueError, match="max_chars"):
        sensitive(max_chars=-1)


def test_sensitive_rejects_char_non_str() -> None:
    with pytest.raises(TypeError, match="char"):
        sensitive(char=42)  # type: ignore[arg-type, call-overload]


def test_sensitive_rejects_multi_char_string() -> None:
    with pytest.raises(ValueError, match="char"):
        sensitive(char="**")


def test_sensitive_rejects_max_percent_non_int() -> None:
    with pytest.raises(TypeError, match="max_percent"):
        sensitive(max_percent=50.5)  # type: ignore[arg-type, call-overload]


def test_sensitive_rejects_max_percent_out_of_range() -> None:
    with pytest.raises(ValueError, match=r"0\.\.100"):
        sensitive(max_percent=101)


def test_sensitive_on_property_without_getter_raises() -> None:
    prop = property(fget=None)

    with pytest.raises(TypeError, match="getter"):
        sensitive()(prop)


def test_sensitive_rejects_non_callable_non_property() -> None:
    with pytest.raises(TypeError, match="property"):
        sensitive()(object())  # type: ignore[arg-type, call-overload]


def test_sensitive_on_callable_attaches_config() -> None:
    def getter(_self) -> str:
        return "x"

    out = sensitive(max_chars=2)(getter)
    assert out is getter
    assert getter._sensitive_config["max_chars"] == 2


def test_sensitive_on_property_wraps_same_getter() -> None:
    def getter(_self) -> str:
        return "secret"

    prop = property(getter)
    wrapped = sensitive(max_chars=1)(prop)
    assert isinstance(wrapped, property)
    assert wrapped.fget is getter
    assert getter._sensitive_config["max_chars"] == 1
