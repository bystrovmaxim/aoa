"""Constructor, frozen semantics, dict-like access, and the ResolveItemResult
base class relationship for AccessVerdict."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from aoa.action_machine.intents.access_control import AccessVerdict, ResolveItemKind, ResolveItemResult

from ....support.domain_model.ping_action import PingAction


class TestAccessVerdictCreation:
    """Constructing AccessVerdict for allowed and denied outcomes."""

    def test_success_verdict_carries_empty_reason(self) -> None:
        verdict = AccessVerdict(action=PingAction, kind=ResolveItemKind.SUCCESS, reason="")
        assert verdict.kind == ResolveItemKind.SUCCESS
        assert verdict.action is PingAction
        assert verdict.reason == ""

    def test_denied_verdict_carries_kind_and_reason(self) -> None:
        verdict = AccessVerdict(action=PingAction, kind=ResolveItemKind.SECURITY, reason="not your order")
        assert verdict.kind == ResolveItemKind.SECURITY
        assert verdict.reason == "not your order"

    def test_kind_and_reason_are_both_required(self) -> None:
        with pytest.raises(ValidationError):
            AccessVerdict(action=PingAction, kind=ResolveItemKind.SUCCESS)  # type: ignore[call-arg]
        with pytest.raises(ValidationError):
            AccessVerdict(action=PingAction, reason="")  # type: ignore[call-arg]

    def test_extra_field_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            AccessVerdict(  # type: ignore[call-arg]
                action=PingAction, kind=ResolveItemKind.SUCCESS, reason="", extra_field="nope"
            )


class TestAccessVerdictReasonMatchesKind:
    """Audit finding 3, second line of defense: kind=SUCCESS <=> reason="" is an
    enforced invariant, not only a promise in the class docstring."""

    def test_success_with_non_empty_reason_raises(self) -> None:
        with pytest.raises(ValidationError, match="kind=SUCCESS"):
            AccessVerdict(action=PingAction, kind=ResolveItemKind.SUCCESS, reason="should be empty")

    def test_non_success_with_empty_reason_raises(self) -> None:
        with pytest.raises(ValidationError, match="non-empty reason"):
            AccessVerdict(action=PingAction, kind=ResolveItemKind.SECURITY, reason="")


class TestAccessVerdictFrozen:
    """AccessVerdict is immutable after construction."""

    def test_mutation_raises_validation_error(self) -> None:
        verdict = AccessVerdict(action=PingAction, kind=ResolveItemKind.SUCCESS, reason="")
        with pytest.raises(ValidationError):
            verdict.kind = ResolveItemKind.SECURITY


class TestAccessVerdictDictAccess:
    """BaseSchema dict-like access on AccessVerdict."""

    def test_getitem(self) -> None:
        verdict = AccessVerdict(action=PingAction, kind=ResolveItemKind.SECURITY, reason="wrong role")
        assert verdict["kind"] == ResolveItemKind.SECURITY
        assert verdict["reason"] == "wrong role"

    def test_getitem_missing_raises_key_error(self) -> None:
        verdict = AccessVerdict(action=PingAction, kind=ResolveItemKind.SUCCESS, reason="")
        with pytest.raises(KeyError):
            _ = verdict["nonexistent"]

    def test_contains(self) -> None:
        verdict = AccessVerdict(action=PingAction, kind=ResolveItemKind.SUCCESS, reason="")
        assert "kind" in verdict
        assert "nonexistent" not in verdict


class TestAccessVerdictIsAResolveItemResult:
    """AccessVerdict subclasses ResolveItemResult -- one entity, not two types kept
    in sync by hand (to_wire() used to copy between them; it is gone now)."""

    def test_access_verdict_is_a_resolve_item_result(self) -> None:
        verdict = AccessVerdict(action=PingAction, kind=ResolveItemKind.SUCCESS, reason="")
        assert isinstance(verdict, ResolveItemResult)

    def test_action_is_excluded_from_serialization(self) -> None:
        """`.action` is a live Python class reference -- meaningful only inside this
        process, never on the wire. model_dump()/model_dump_json() drop it
        unconditionally, regardless of the field's declared type on whatever
        container holds this instance (e.g. ResolveResponse.results: list[ResolveItemResult]
        in aoa-fastapi-adapter, which can now hold AccessVerdict instances directly)."""
        verdict = AccessVerdict(action=PingAction, kind=ResolveItemKind.SECURITY, reason="not a manager")
        dumped = verdict.model_dump()
        assert "action" not in dumped
        assert dumped == {"kind": ResolveItemKind.SECURITY, "reason": "not a manager"}
        assert "action" not in verdict.model_dump_json()

    def test_base_class_validator_applies_to_the_subclass_without_redeclaring_it(self) -> None:
        """The kind/reason validator lives once, on ResolveItemResult -- AccessVerdict
        does not redeclare it, and it still fires (fix-audit finding 7)."""
        with pytest.raises(ValidationError, match="kind=SUCCESS"):
            AccessVerdict(action=PingAction, kind=ResolveItemKind.SUCCESS, reason="should be empty")

    def test_resolve_item_result_alone_has_no_action_field(self) -> None:
        """The two call sites that build a verdict with no real action behind it at
        all (unknown operation, route-level auth rejection before the action
        resolved) construct ResolveItemResult directly -- it never had an `action`
        slot to fill, so there is nothing to work around for them."""
        result = ResolveItemResult(kind=ResolveItemKind.CHECK_ERROR, reason="UNKNOWN_ENDPOINT")
        assert "action" not in result.model_dump()
        with pytest.raises(ValidationError):
            ResolveItemResult(action=PingAction, kind=ResolveItemKind.CHECK_ERROR, reason="UNKNOWN_ENDPOINT")  # type: ignore[call-arg]


class TestResolveItemKindTsParity:
    """chapter 3.5's acceptance list calls for a fixture asserting the server's
    ResolveItemKind StrEnum values match chapter 4's TypeScript client enum verbatim.

    Blocked, not merely unwritten: no aoa-client-js (or any generated TypeScript
    client) exists anywhere in this repo yet — chapter 4 is still design-only.
    There is nothing to compare ``[k.value for k in ResolveItemKind]`` against.
    Once the TS client exists, replace this skip with a real fixture shared by
    both languages' test suites (see chapter 3.5, "2.2 Серверный приёмочный набор
    тестов").
    """

    @pytest.mark.skip(reason="No TypeScript client package exists yet (chapter 4 is design-only)")
    def test_server_kind_values_match_the_ts_enum(self) -> None:
        raise NotImplementedError
