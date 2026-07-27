"""BaseVerdict hierarchy: AllowedVerdict, FailSecurityVerdict, FailErrorVerdict."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import pytest
from pydantic import Field, ValidationError

from aoa.action_machine.intents.access_control import (
    FORBIDDEN_OBJECT,
    AllowedVerdict,
    BaseVerdict,
    FailErrorVerdict,
    FailSecurityVerdict,
)


class TestKind:
    """kind: the name of the answer, as it goes out on the wire.

    BaseVerdict has no value of its own for it, so constructing one takes an explicit
    kind. Nothing stops that, and nothing needs to: a bare BaseVerdict is not one of the
    two classes run() accepts, so it is refused there -- see
    test_action_product_machine_access_decide.py.
    """

    def test_base_verdict_has_no_kind_of_its_own(self) -> None:
        with pytest.raises(ValidationError):
            BaseVerdict()

    def test_each_concrete_class_declares_its_own_wire_name(self) -> None:
        """The default a caller gets when they pass nothing."""
        assert AllowedVerdict().kind == "AllowedVerdict"
        assert FailSecurityVerdict("reason").kind == "FailSecurityVerdict"
        assert FailErrorVerdict("reason").kind == "FailErrorVerdict"

    @pytest.mark.parametrize("given", ["OldWireName", "", "ЧтоУгодно 123 !@#"])
    def test_kind_stores_whatever_it_is_given(self, given: str) -> None:
        """kind is a plain stored string, not a closed set: it takes any value and keeps
        it verbatim. That is what makes a class renameable without renaming what goes
        out on the wire. Which values an adapter will *accept* off the wire is that
        adapter's business, not this class's."""
        assert AllowedVerdict(kind=given).kind == given
        assert AllowedVerdict(kind=given).model_dump() == {"kind": given}

    def test_a_subclass_can_pin_its_own_wire_name(self) -> None:
        """The same freedom, declared once on the class instead of at every call site."""

        class Legacy(FailSecurityVerdict):
            kind: str = Field(default="OldWireName")

        assert Legacy("no").kind == "OldWireName"
        assert Legacy("no").model_dump() == {"kind": "OldWireName", "reason": "no"}


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
        """The positional `reason` constructor still works without an override, since
        FailSecurityVerdict.__init__ passes extra fields through **kwargs.

        kind keeps saying FailSecurityVerdict: a subclass that only adds a field is
        still that kind of answer, and a client is not required to have heard of the
        subclass to read it. A subclass that genuinely is a different kind says so by
        declaring its own -- see test_a_subclass_can_pin_its_own_wire_name.
        """

        class OwnershipDenied(FailSecurityVerdict):
            order_id: int

        verdict = OwnershipDenied("not your order", order_id=7)
        assert verdict.kind == "FailSecurityVerdict"
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


class TestForbiddenObject:
    """The shared object-level denial. Owned by this package, so pinned here rather than
    only through aoa-demo's usage of it."""

    def test_is_a_security_denial_not_an_error(self) -> None:
        """The class carries the meaning: a denial is cacheable, an error is not. Typed as
        FailErrorVerdict this would become a never-cached non-answer, and any test that
        only checks .reason would stay green."""
        assert isinstance(FORBIDDEN_OBJECT, FailSecurityVerdict)
        assert not isinstance(FORBIDDEN_OBJECT, FailErrorVerdict)
        assert FORBIDDEN_OBJECT.kind == "FailSecurityVerdict"

    def test_reason_is_the_fixed_code(self) -> None:
        assert FORBIDDEN_OBJECT.reason == "FORBIDDEN_OBJECT"

    def test_dumped_shape(self) -> None:
        """The exact bytes a client receives for both "missing" and "foreign"."""
        assert FORBIDDEN_OBJECT.model_dump() == {"kind": "FailSecurityVerdict", "reason": "FORBIDDEN_OBJECT"}

    def test_round_trips_through_its_own_dump(self) -> None:
        """Same guarantee the other verdicts get tested for, applied to the shared instance."""
        restored = FailSecurityVerdict.model_validate(FORBIDDEN_OBJECT.model_dump())
        assert restored == FORBIDDEN_OBJECT

    def test_is_frozen_so_one_shared_instance_is_safe_to_hand_out(self) -> None:
        """Why a module-level singleton is safe at all: nobody can mutate it in place."""
        with pytest.raises(ValidationError):
            FORBIDDEN_OBJECT.reason = "something else"  # type: ignore[misc]

    def test_model_copy_and_model_construct_do_not_poison_the_shared_instance(self) -> None:
        """These skip validation and frozen=True, but return a new object instead of mutating,
        so the shared instance survives. Pydantic's behaviour, not ours -- an upgrade could
        change it."""
        copied = FORBIDDEN_OBJECT.model_copy(update={"reason": "SOMETHING ELSE"})
        constructed = FailSecurityVerdict.model_construct(kind="FailSecurityVerdict", reason="")

        assert copied is not FORBIDDEN_OBJECT
        assert constructed is not FORBIDDEN_OBJECT
        assert FORBIDDEN_OBJECT.reason == "FORBIDDEN_OBJECT"

    def test_the_export_and_the_definition_are_the_same_object(self) -> None:
        """Callers compare by identity (`verdict is FORBIDDEN_OBJECT`), so the re-export
        must not be a copy -- two constants would silently break every such comparison."""
        from aoa.action_machine.intents.access_control import access_verdict

        assert FORBIDDEN_OBJECT is access_verdict.FORBIDDEN_OBJECT

    @pytest.mark.parametrize(
        "poison",
        [
            pytest.param(lambda v: object.__setattr__(v, "reason", "ORDER 42 IS NOT YOURS"), id="object.__setattr__"),
            pytest.param(lambda v: v.__dict__.__setitem__("reason", "ORDER 42 IS NOT YOURS"), id="__dict__"),
        ],
    )
    def test_in_place_mutation_of_the_shared_instance_is_a_process_wide_leak(self, poison: Callable[[Any], None]) -> None:
        """The two routes that get past ``frozen=True`` and write into the singleton itself.

        Every later denial in the process then carries the new text, so "missing" and
        "foreign" stop answering identically and the object-level denial becomes an oracle.
        """
        from aoa.action_machine.intents.access_control import access_verdict

        original = FORBIDDEN_OBJECT.reason
        try:
            poison(FORBIDDEN_OBJECT)
            assert FORBIDDEN_OBJECT.reason != original, "route no longer bypasses frozen -- rewrite this test"
            assert access_verdict.FORBIDDEN_OBJECT.reason != original, "the whole process sees the poisoned value"
        finally:
            object.__setattr__(FORBIDDEN_OBJECT, "reason", original)
        assert FORBIDDEN_OBJECT.reason == original


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
        """kind is a real field, so keys()/items() see it -- BaseSchema's dict-like access
        only looks at declared model_fields."""
        verdict = AllowedVerdict()
        assert verdict.keys() == ["kind"]
        assert verdict.items() == [("kind", "AllowedVerdict")]


class TestJsonRoundTrip:
    def test_fail_security_verdict_model_dump_json(self) -> None:
        verdict = FailSecurityVerdict("not a manager")
        dumped = json.loads(verdict.model_dump_json())
        assert dumped == {"kind": "FailSecurityVerdict", "reason": "not a manager"}

    def test_model_dump_round_trips_through_model_validate(self) -> None:
        """A verdict can be reconstructed from its own wire shape: extra="forbid" would
        reject kind on the way back if it were not a declared field."""
        verdict = FailSecurityVerdict("FORBIDDEN_ROLE")
        assert FailSecurityVerdict.model_validate(verdict.model_dump()) == verdict
