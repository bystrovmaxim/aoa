"""Constructor and .reason property for AccessDeniedError."""

from __future__ import annotations

import pytest

from aoa.action_machine.exceptions import AccessDeniedError, AccessGate
from aoa.action_machine.intents.access_control import AllowedVerdict, FailSecurityVerdict


def _denial(**overrides: object) -> AccessDeniedError:
    args: dict[str, object] = {
        "message": "Access denied. Required role: 'Admin'.",
        "refused_by": AccessGate.CHECK_ROLES,
        "verdict": FailSecurityVerdict("FORBIDDEN_ROLE"),
    }
    args.update(overrides)
    message = args.pop("message")
    return AccessDeniedError(message, **args)  # type: ignore[arg-type]


class TestAllThreePartsAreRequired:
    """A refusal that cannot say who refused, or why, is not one anybody can act on."""

    @pytest.mark.parametrize("missing", ["refused_by", "verdict", "both"])
    def test_omitting_any_of_them_is_refused(self, missing: str) -> None:
        """Not defaulted to None: leaving one out is a call that cannot be built at all,
        so the mistake surfaces where it is made rather than wherever it is read."""
        kwargs: dict[str, object] = {
            "refused_by": AccessGate.CHECK_ROLES,
            "verdict": FailSecurityVerdict("FORBIDDEN_ROLE"),
        }
        if missing == "both":
            kwargs.clear()
        else:
            kwargs.pop(missing)

        with pytest.raises(TypeError, match="required keyword-only argument"):
            AccessDeniedError("denied", **kwargs)  # type: ignore[arg-type]

    def test_all_three_are_stored_and_readable(self) -> None:
        err = _denial()
        assert str(err) == "Access denied. Required role: 'Admin'."
        assert err.refused_by is AccessGate.CHECK_ROLES
        assert err.verdict == FailSecurityVerdict("FORBIDDEN_ROLE")
        assert err.reason == "FORBIDDEN_ROLE"

    def test_the_message_and_the_reason_carry_different_things(self) -> None:
        """The message is the sentence a person reads; the reason is the code a program
        matches on. Both are kept, and neither stands in for the other."""
        err = _denial(message="this order is locked", verdict=FailSecurityVerdict("ORDER_LOCKED"))

        assert str(err) == "this order is locked"
        assert err.reason == "ORDER_LOCKED"


class TestMessage:
    @pytest.mark.parametrize(
        "message",
        [
            pytest.param("", id="empty"),
            pytest.param("   ", id="spaces"),
            pytest.param("\t\n", id="whitespace"),
            pytest.param(None, id="None"),
            pytest.param(123, id="a number"),
        ],
    )
    def test_a_message_that_says_nothing_is_refused(self, message: object) -> None:
        """It is the text a person sees when this is raised. Blank, the failure arrives
        describing nothing, and the verdict's reason does not stand in for it -- that is a
        code for a program, not a sentence for a reader."""
        with pytest.raises(ValueError, match="message="):
            _denial(message=message)


class TestRefusedBy:
    @pytest.mark.parametrize("gate", list(AccessGate))
    def test_every_gate_is_accepted(self, gate: AccessGate) -> None:
        assert _denial(refused_by=gate).refused_by is gate

    def test_the_value_is_what_goes_out_to_the_caller(self) -> None:
        """It is a string, so a refusal reads without a table to decode it."""
        assert _denial(refused_by=AccessGate.ACCESS_DECIDE).refused_by == "ACCESS_DECIDE"

    @pytest.mark.parametrize(
        "refused_by",
        [
            pytest.param("ACCESS_DECIDE", id="the right text, but a plain string"),
            pytest.param("no such gate", id="text naming nothing"),
            pytest.param(3, id="a number"),
            pytest.param(True, id="a bool"),
            pytest.param(None, id="None"),
        ],
    )
    def test_anything_that_is_not_a_gate_is_refused(self, refused_by: object) -> None:
        """It answers "which check said no", so it has to BE one of them. A bare string
        that happens to spell one is refused too -- it would leave the caller unable to
        tell a real answer from a typo somewhere upstream."""
        with pytest.raises(ValueError, match="refused_by="):
            _denial(refused_by=refused_by)


class TestVerdict:
    def test_a_plain_string_is_refused(self) -> None:
        """It would sail through and crash the first time anything read .reason off it --
        in the shared denial handler that runs for every refusal."""
        with pytest.raises(TypeError, match="FailSecurityVerdict"):
            _denial(verdict="not a verdict object")

    def test_an_allow_is_refused(self) -> None:
        """A real verdict class, just the wrong one. An allow attached to a refusal is a
        contradiction, and reading it back would report the call as permitted."""
        with pytest.raises(TypeError, match="FailSecurityVerdict"):
            _denial(verdict=AllowedVerdict())

    def test_none_is_refused(self) -> None:
        """There is no such thing as a refusal that cannot say why. Without a verdict,
        whatever reads this cannot tell a denial from a crash."""
        with pytest.raises(TypeError, match="FailSecurityVerdict"):
            _denial(verdict=None)

    def test_a_subclass_carrying_extra_fields_is_accepted(self) -> None:
        """Refusals are free to say more than the reason -- only the base shape is required."""

        class OwnershipDenied(FailSecurityVerdict):
            order_id: int

        err = _denial(verdict=OwnershipDenied("FORBIDDEN_OBJECT", order_id=7))

        assert err.reason == "FORBIDDEN_OBJECT"
        assert err.verdict.order_id == 7  # type: ignore[attr-defined]
