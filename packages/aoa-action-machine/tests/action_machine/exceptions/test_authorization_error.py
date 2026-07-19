"""Constructor and .reason property for AuthorizationError."""

from __future__ import annotations

from aoa.action_machine.exceptions import AuthorizationError
from aoa.action_machine.intents.access_control import FailSecurityVerdict


def test_message_and_level_and_verdict_stored() -> None:
    err = AuthorizationError("role gate failed", level=1, verdict=FailSecurityVerdict("FORBIDDEN_ROLE"))
    assert str(err) == "role gate failed"
    assert err.level == 1
    assert err.verdict == FailSecurityVerdict("FORBIDDEN_ROLE")
    assert err.reason == "FORBIDDEN_ROLE"


def test_level_and_verdict_default_to_none() -> None:
    err = AuthorizationError("access denied")
    assert err.level is None
    assert err.verdict is None
    assert err.reason is None


def test_message_without_verdict_is_fine() -> None:
    """The route-level/entry-gate auth failures raised outside RoleChecker
    (e.g. auth_coordinator rejection) carry no verdict at all."""
    err = AuthorizationError("Authentication required")
    assert err.verdict is None
    assert err.reason is None


def test_empty_message_with_a_verdict_is_fine() -> None:
    """No message/verdict cross-validation any more -- FailSecurityVerdict's own
    Field(min_length=1) already guarantees reason is never empty when a verdict
    is given at all, so there is nothing left for this exception to police."""
    err = AuthorizationError("", verdict=FailSecurityVerdict("order is locked"))
    assert str(err) == ""
    assert err.reason == "order is locked"
