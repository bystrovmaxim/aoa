"""Constructor validation for AuthorizationError."""

from __future__ import annotations

import pytest

from aoa.action_machine.exceptions import AuthorizationError


def test_message_and_level_and_reason_stored() -> None:
    err = AuthorizationError("role gate failed", level=1, reason="FORBIDDEN_ROLE")
    assert str(err) == "role gate failed"
    assert err.level == 1
    assert err.reason == "FORBIDDEN_ROLE"


def test_level_and_reason_default_to_none() -> None:
    err = AuthorizationError("access denied")
    assert err.level is None
    assert err.reason is None


def test_message_without_reason_is_fine() -> None:
    err = AuthorizationError("Access denied: SomeAction.access_decide() returned False.")
    assert err.reason is None


def test_reason_without_message_is_fine() -> None:
    err = AuthorizationError("", reason="order is locked")
    assert str(err) == ""
    assert err.reason == "order is locked"


def test_empty_message_and_no_reason_raises() -> None:
    with pytest.raises(ValueError, match="message and reason cannot both be empty"):
        AuthorizationError("")


def test_empty_message_and_empty_reason_raises() -> None:
    with pytest.raises(ValueError, match="message and reason cannot both be empty"):
        AuthorizationError("", reason="")
