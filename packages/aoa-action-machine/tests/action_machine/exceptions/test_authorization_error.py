"""Constructor and .reason property for AuthorizationError."""

from __future__ import annotations

import pytest

from aoa.action_machine.exceptions import AuthorizationError
from aoa.action_machine.intents.access_control import AllowedVerdict, FailSecurityVerdict


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
    """An empty message is fine as long as a verdict is given -- the exception has
    somewhere to point a reader for a real description of what went wrong."""
    err = AuthorizationError("", verdict=FailSecurityVerdict("order is locked"))
    assert str(err) == ""
    assert err.reason == "order is locked"


def test_empty_message_without_verdict_raises() -> None:
    """message="" and verdict=None together leave nothing describing the failure --
    rejected at construction (audit finding 1, third document: this guard was lost
    as a side effect of the BaseVerdict refactor renaming its own reason= parameter
    to verdict=, and silently reopened the batch-crashing bug it was written to close)."""
    with pytest.raises(ValueError, match="cannot both be empty"):
        AuthorizationError("")


def test_verdict_as_plain_string_raises() -> None:
    """baseverdict-audit finding 2, fourth document: verdict= was only checked for
    absence (is None), never for type -- a plain string sailed through construction
    and crashed the first time something read .reason off it, in the shared HTTP
    403 handler that runs for every real denial."""
    with pytest.raises(TypeError, match="FailSecurityVerdict"):
        AuthorizationError("denied", verdict="not a verdict object")  # type: ignore[arg-type]


def test_verdict_as_allowed_verdict_raises() -> None:
    """Same gap, the other reproduced shape: an AllowedVerdict (a real BaseVerdict
    subclass, just the wrong one -- an allow, not a denial) must also be rejected,
    not only values of the wrong type entirely."""
    with pytest.raises(TypeError, match="FailSecurityVerdict"):
        AuthorizationError("denied", verdict=AllowedVerdict())  # type: ignore[arg-type]
