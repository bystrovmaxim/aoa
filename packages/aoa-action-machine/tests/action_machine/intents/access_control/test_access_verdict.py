"""Constructor, frozen semantics, and dict-like access for AccessVerdict."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from aoa.action_machine.intents.access_control import AccessVerdict, ResolveItemKind

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
            verdict.kind = ResolveItemKind.SECURITY  # type: ignore[misc]


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
