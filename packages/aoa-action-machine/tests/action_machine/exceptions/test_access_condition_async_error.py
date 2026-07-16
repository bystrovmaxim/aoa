"""Constructor, message, and inheritance for AccessConditionAsyncError."""

from __future__ import annotations

import pytest

from aoa.action_machine.exceptions import AccessConditionAsyncError


async def _condition(user: object) -> bool:
    return True


def test_stores_condition_name_and_func() -> None:
    err = AccessConditionAsyncError("guard", _condition)
    assert err.condition_name == "guard"
    assert err.func is _condition


def test_message_names_condition_and_function() -> None:
    err = AccessConditionAsyncError("when", _condition)
    assert "when" in str(err)
    assert "_condition" in str(err)
    assert "async def" in str(err)


def test_is_type_error_and_raisable() -> None:
    assert issubclass(AccessConditionAsyncError, TypeError)
    with pytest.raises(AccessConditionAsyncError):
        raise AccessConditionAsyncError("guard", _condition)
