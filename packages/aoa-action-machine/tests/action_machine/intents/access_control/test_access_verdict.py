"""Constructor, frozen semantics, and dict-like access for AccessVerdict."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from aoa.action_machine.intents.access_control import AccessVerdict

from ....support.domain_model.ping_action import PingAction


class TestAccessVerdictCreation:
    """Constructing AccessVerdict for allowed and denied outcomes."""

    def test_allowed_verdict_defaults_level_and_reason_to_none(self) -> None:
        verdict = AccessVerdict(allowed=True, action=PingAction)
        assert verdict.allowed is True
        assert verdict.action is PingAction
        assert verdict.level is None
        assert verdict.reason is None

    def test_denied_verdict_carries_level_and_reason(self) -> None:
        verdict = AccessVerdict(allowed=False, action=PingAction, level=3, reason="not your order")
        assert verdict.allowed is False
        assert verdict.level == 3
        assert verdict.reason == "not your order"

    def test_extra_field_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            AccessVerdict(allowed=True, action=PingAction, extra_field="nope")  # type: ignore[call-arg]


class TestAccessVerdictFrozen:
    """AccessVerdict is immutable after construction."""

    def test_mutation_raises_validation_error(self) -> None:
        verdict = AccessVerdict(allowed=True, action=PingAction)
        with pytest.raises(ValidationError):
            verdict.allowed = False  # type: ignore[misc]


class TestAccessVerdictDictAccess:
    """BaseSchema dict-like access on AccessVerdict."""

    def test_getitem(self) -> None:
        verdict = AccessVerdict(allowed=False, action=PingAction, level=1, reason="wrong role")
        assert verdict["level"] == 1
        assert verdict["reason"] == "wrong role"

    def test_getitem_missing_raises_key_error(self) -> None:
        verdict = AccessVerdict(allowed=True, action=PingAction)
        with pytest.raises(KeyError):
            _ = verdict["nonexistent"]

    def test_contains(self) -> None:
        verdict = AccessVerdict(allowed=True, action=PingAction)
        assert "level" in verdict
        assert "nonexistent" not in verdict
