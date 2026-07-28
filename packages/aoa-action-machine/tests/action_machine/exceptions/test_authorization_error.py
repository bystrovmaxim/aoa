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


def test_the_message_and_the_verdict_carry_different_things() -> None:
    """The message is the sentence a person reads; the verdict's reason is the code a
    program matches on. Both are kept, neither replaces the other."""
    err = AuthorizationError("this order is locked", verdict=FailSecurityVerdict("ORDER_LOCKED"))
    assert str(err) == "this order is locked"
    assert err.reason == "ORDER_LOCKED"


@pytest.mark.parametrize("message", ["", "   ", "\t\n", None, 123])
def test_a_message_that_says_nothing_is_refused(message: object) -> None:
    """message is the text a person sees when this is raised. Blank, the failure arrives
    describing nothing -- and a reason on the verdict does not help, since that is a code
    for a program, not a sentence for a reader."""
    with pytest.raises(ValueError, match="message="):
        AuthorizationError(message)  # type: ignore[arg-type]


def test_a_message_is_required_even_when_a_verdict_is_given() -> None:
    """The two are not interchangeable, so carrying one does not excuse the other."""
    with pytest.raises(ValueError, match="message="):
        AuthorizationError("", verdict=FailSecurityVerdict("FORBIDDEN_ROLE"))


def test_verdict_as_plain_string_raises() -> None:
    """A plain string would sail through and crash the first time anything read .reason
    off it -- in the shared 403 handler that runs for every real denial."""
    with pytest.raises(TypeError, match="FailSecurityVerdict"):
        AuthorizationError("denied", verdict="not a verdict object")  # type: ignore[arg-type]


def test_verdict_as_allowed_verdict_raises() -> None:
    """Same gap, the other reproduced shape: an AllowedVerdict (a real BaseVerdict
    subclass, just the wrong one -- an allow, not a denial) must also be rejected,
    not only values of the wrong type entirely."""
    with pytest.raises(TypeError, match="FailSecurityVerdict"):
        AuthorizationError("denied", verdict=AllowedVerdict())  # type: ignore[arg-type]


@pytest.mark.parametrize("level", [1, 2, 3, None])
def test_a_level_naming_a_real_gate_is_accepted(level: int | None) -> None:
    """Three gates decide access, and None means the refusal came from in front of them."""
    assert AuthorizationError("denied", level=level).level == level


@pytest.mark.parametrize("level", [0, 4, 99, -1, "two", 1.0, True])
def test_a_level_naming_no_gate_is_refused(level: object) -> None:
    """level answers "which gate said no", so a value naming no gate answers nothing and
    a caller cannot tell it apart from a real answer. True and 1.0 are refused too: both
    equal 1 in Python and would be stored as a level that was never passed."""
    with pytest.raises(ValueError, match="level="):
        AuthorizationError("denied", level=level)  # type: ignore[arg-type]
