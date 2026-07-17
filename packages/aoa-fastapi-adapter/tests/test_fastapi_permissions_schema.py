# tests/test_fastapi_permissions_schema.py
"""
Tests for ``aoa.fastapi.permissions_schema`` — ``/permissions/resolve`` wire models (issue #130, PR 1).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Validate required/default fields, the non-empty ``items`` invariant, extra-field
rejection, and that ``Verdict``'s reserved fields (``scope``, ``entities``,
``reason_code``, ``expires_at``) default to their PR-1 "unpopulated" values.
"""

import pytest
from pydantic import ValidationError

from aoa.fastapi.permissions_schema import ResolveItem, ResolveRequest, ResolveResponse, Verdict


class TestResolveItem:
    """``ResolveItem`` — one question in a resolve batch."""

    def test_operation_required(self) -> None:
        """``operation`` is mandatory."""
        with pytest.raises(ValidationError):
            ResolveItem(params={"order_id": 7})  # type: ignore[call-arg]

    def test_params_defaults_to_empty_dict(self) -> None:
        """``params`` defaults to ``{}`` when omitted."""
        item = ResolveItem(operation="POST /actions/cancel-order")
        assert item.params == {}

    def test_context_defaults_to_none(self) -> None:
        """``context`` (reserved for future ABAC hints) defaults to ``None``."""
        item = ResolveItem(operation="POST /actions/cancel-order")
        assert item.context is None

    def test_rejects_extra_fields(self) -> None:
        """Unknown wire fields are rejected, not silently ignored."""
        with pytest.raises(ValidationError):
            ResolveItem(operation="POST /actions/cancel-order", unexpected="value")  # type: ignore[call-arg]


class TestResolveRequest:
    """``ResolveRequest`` — the resolver's request body."""

    def test_requires_at_least_one_item(self) -> None:
        """An empty ``items`` list is rejected (FR: batch of 1..N, never 0)."""
        with pytest.raises(ValidationError):
            ResolveRequest(protocol=1, items=[])

    def test_batch_of_one_is_valid(self) -> None:
        """A single-item batch is the ordinary case, not a special one."""
        request = ResolveRequest(protocol=1, items=[ResolveItem(operation="POST /actions/cancel-order")])
        assert len(request.items) == 1

    def test_batch_of_many_preserves_order(self) -> None:
        """Multiple items round-trip in the order they were given."""
        request = ResolveRequest(
            protocol=1,
            items=[
                ResolveItem(operation="POST /actions/cancel-order", params={"order_id": 1}),
                ResolveItem(operation="POST /actions/issue-refund", params={"order_id": 1}),
            ],
        )
        assert [item.operation for item in request.items] == ["POST /actions/cancel-order", "POST /actions/issue-refund"]

    def test_rejects_extra_fields(self) -> None:
        """Unknown top-level wire fields are rejected."""
        with pytest.raises(ValidationError):
            ResolveRequest(  # type: ignore[call-arg]
                protocol=1,
                items=[ResolveItem(operation="POST /actions/cancel-order")],
                unexpected="value",
            )


class TestVerdict:
    """``Verdict`` — one answer, with PR-1's reserved-but-unpopulated fields."""

    def test_only_allowed_is_required(self) -> None:
        """``allowed`` is the only field a caller must supply."""
        verdict = Verdict(allowed=True)
        assert verdict.allowed is True

    def test_reserved_fields_default_to_unpopulated(self) -> None:
        """PR 1 never populates scope/entities/reason_code/expires_at for real."""
        verdict = Verdict(allowed=False)
        assert verdict.scope is None
        assert verdict.level is None
        assert verdict.reason is None
        assert verdict.reason_code is None
        assert verdict.entities == []
        assert verdict.expires_at is None

    def test_scope_rejects_values_outside_role_or_object(self) -> None:
        """``scope`` is constrained to the two documented wire values."""
        with pytest.raises(ValidationError):
            Verdict(allowed=False, scope="admin")  # type: ignore[arg-type]

    def test_level_rejects_values_outside_one_two_three(self) -> None:
        """``level`` is constrained to the three cascade levels."""
        with pytest.raises(ValidationError):
            Verdict(allowed=False, level=4)  # type: ignore[arg-type]

    def test_rejects_extra_fields(self) -> None:
        """Unknown wire fields are rejected, not silently ignored."""
        with pytest.raises(ValidationError):
            Verdict(allowed=True, unexpected="value")  # type: ignore[call-arg]


class TestResolveResponse:
    """``ResolveResponse`` — the resolver's response body."""

    def test_verdicts_preserve_order(self) -> None:
        """Verdicts round-trip in the order they were given, matching request items positionally."""
        response = ResolveResponse(protocol=1, verdicts=[Verdict(allowed=True), Verdict(allowed=False)])
        assert [v.allowed for v in response.verdicts] == [True, False]

    def test_rejects_extra_fields(self) -> None:
        """Unknown top-level wire fields are rejected."""
        with pytest.raises(ValidationError):
            ResolveResponse(protocol=1, verdicts=[], unexpected="value")  # type: ignore[call-arg]
