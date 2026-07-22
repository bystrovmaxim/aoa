"""BaseVerdict hierarchy: AllowedVerdict, FailSecurityVerdict, FailErrorVerdict."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from aoa.action_machine.intents.access_control import AllowedVerdict, BaseVerdict, FailErrorVerdict, FailSecurityVerdict


class TestBaseVerdictIsAbstract:
    """BaseVerdict cannot be instantiated directly -- only its concrete subclasses can."""

    def test_base_verdict_construction_raises(self) -> None:
        with pytest.raises(TypeError, match="abstract"):
            BaseVerdict()

    def test_kind_is_derived_from_the_subclass_name_without_redeclaration(self) -> None:
        """kind is filled in by BaseVerdict.__init__, inherited by every subclass --
        not a free field a caller could set to a mismatched value."""
        assert AllowedVerdict().kind == "AllowedVerdict"
        assert FailSecurityVerdict("reason").kind == "FailSecurityVerdict"
        assert FailErrorVerdict("reason").kind == "FailErrorVerdict"

    def test_mismatched_explicit_kind_raises(self) -> None:
        """A caller cannot lie about kind through the normal constructor -- kind is
        derived from the class being built, not a settable field."""
        with pytest.raises(ValueError, match="kind must be 'AllowedVerdict'"):
            AllowedVerdict(kind="FailSecurityVerdict")  # type: ignore[call-arg]


class TestAllowedVerdict:
    """The one way to say "yes" -- no reason field at all."""

    def test_construction_takes_no_parameters(self) -> None:
        verdict = AllowedVerdict()
        assert verdict.kind == "AllowedVerdict"

    def test_has_no_reason_field(self) -> None:
        with pytest.raises(ValidationError):
            AllowedVerdict(reason="anything")  # type: ignore[call-arg]

    def test_dumped_shape_is_exactly_kind(self) -> None:
        assert AllowedVerdict().model_dump() == {"kind": "AllowedVerdict"}


class TestFailSecurityVerdict:
    """A real access-control denial -- reason mandatory and non-empty."""

    def test_construction_positional(self) -> None:
        verdict = FailSecurityVerdict("FORBIDDEN_ROLE")
        assert verdict.kind == "FailSecurityVerdict"
        assert verdict.reason == "FORBIDDEN_ROLE"

    def test_empty_reason_raises(self) -> None:
        with pytest.raises(ValidationError):
            FailSecurityVerdict("")

    def test_dumped_shape(self) -> None:
        assert FailSecurityVerdict("not your order").model_dump() == {
            "kind": "FailSecurityVerdict",
            "reason": "not your order",
        }

    def test_frozen(self) -> None:
        verdict = FailSecurityVerdict("FORBIDDEN_ROLE")
        with pytest.raises(ValidationError):
            verdict.reason = "changed"  # type: ignore[misc]

    def test_subclass_may_add_its_own_fields(self) -> None:
        """Same extensibility BaseVerdict.kind already demonstrates: a subclass adds
        fields, kind keeps resolving to the subclass's own name, no redeclaration --
        and the positional `reason` constructor still works without an override,
        since FailSecurityVerdict.__init__ passes extra fields through **kwargs."""

        class OwnershipDenied(FailSecurityVerdict):
            order_id: int

        verdict = OwnershipDenied("not your order", order_id=7)
        assert verdict.kind == "OwnershipDenied"
        assert verdict.order_id == 7
        assert verdict.reason == "not your order"


class TestFailErrorVerdict:
    """The check itself could not be answered -- not a denial, never cached as one."""

    def test_construction_positional(self) -> None:
        verdict = FailErrorVerdict("UNKNOWN_ENDPOINT")
        assert verdict.kind == "FailErrorVerdict"
        assert verdict.reason == "UNKNOWN_ENDPOINT"

    def test_empty_reason_raises(self) -> None:
        with pytest.raises(ValidationError):
            FailErrorVerdict("")

    def test_dumped_shape(self) -> None:
        assert FailErrorVerdict("KeyError").model_dump() == {"kind": "FailErrorVerdict", "reason": "KeyError"}


class TestDictLikeAccess:
    """BaseSchema dict-like access on a concrete verdict."""

    def test_getitem(self) -> None:
        verdict = FailSecurityVerdict("wrong role")
        assert verdict["kind"] == "FailSecurityVerdict"
        assert verdict["reason"] == "wrong role"

    def test_getitem_missing_raises_key_error(self) -> None:
        verdict = AllowedVerdict()
        with pytest.raises(KeyError):
            _ = verdict["nonexistent"]

    def test_contains(self) -> None:
        verdict = FailSecurityVerdict("wrong role")
        assert "kind" in verdict
        assert "reason" in verdict
        assert "nonexistent" not in verdict

    def test_kind_appears_in_keys_and_items(self) -> None:
        """baseverdict-audit finding 6, third document: kind used to be a
        @computed_field, invisible to BaseSchema's keys()/items() (which only look
        at declared model_fields) even though direct access (verdict["kind"]) always
        worked -- kind is now a real field, so both agree."""
        verdict = AllowedVerdict()
        assert verdict.keys() == ["kind"]
        assert verdict.items() == [("kind", "AllowedVerdict")]


class TestJsonRoundTrip:
    def test_fail_security_verdict_model_dump_json(self) -> None:
        verdict = FailSecurityVerdict("not a manager")
        dumped = json.loads(verdict.model_dump_json())
        assert dumped == {"kind": "FailSecurityVerdict", "reason": "not a manager"}

    def test_model_dump_round_trips_through_model_validate(self) -> None:
        """baseverdict-audit finding 4, third document: kind used to be a
        @computed_field -- present in model_dump() output, but rejected as an
        unknown field (extra="forbid") by model_validate() on the same class, so a
        verdict could never be honestly reconstructed from its own wire shape."""
        verdict = FailSecurityVerdict("FORBIDDEN_ROLE")
        assert FailSecurityVerdict.model_validate(verdict.model_dump()) == verdict
