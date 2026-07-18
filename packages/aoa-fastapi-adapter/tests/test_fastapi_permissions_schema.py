# tests/test_fastapi_permissions_schema.py
"""
Tests for ``aoa.fastapi.permissions_schema`` — ``/permissions/resolve`` wire models (issue #130).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Validate required/default fields, the non-empty ``items`` invariant, extra-field
rejection, and that ``ResolveItemResult`` is always exactly the flat ``{kind,
reason}`` shape — both fields mandatory, no nested union, no fields that only
make sense for some values of ``kind``.
"""

import pytest
from pydantic import ValidationError

from aoa.action_machine.intents.access_control import ResolveItemKind
from aoa.fastapi.permissions_schema import (
    SUPPORTED_VERSION,
    ErrorDetail,
    ErrorEnvelope,
    ResolveItem,
    ResolveItemResult,
    ResolveRequest,
    ResolveResponse,
)


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
            ResolveRequest(version=1, items=[])

    def test_batch_of_one_is_valid(self) -> None:
        """A single-item batch is the ordinary case, not a special one."""
        request = ResolveRequest(version=1, items=[ResolveItem(operation="POST /actions/cancel-order")])
        assert len(request.items) == 1

    def test_batch_of_many_preserves_order(self) -> None:
        """Multiple items round-trip in the order they were given."""
        request = ResolveRequest(
            version=1,
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
                version=1,
                items=[ResolveItem(operation="POST /actions/cancel-order")],
                unexpected="value",
            )


class TestResolveItemResult:
    """``ResolveItemResult`` — one answer, always exactly ``{kind, reason}``."""

    def test_kind_and_reason_are_both_required(self) -> None:
        """Neither field defaults — ``reason=""`` for ``SUCCESS`` must be given explicitly."""
        with pytest.raises(ValidationError):
            ResolveItemResult(kind=ResolveItemKind.SUCCESS)  # type: ignore[call-arg]
        with pytest.raises(ValidationError):
            ResolveItemResult(reason="")  # type: ignore[call-arg]

    def test_success_with_empty_reason_round_trips(self) -> None:
        result = ResolveItemResult(kind=ResolveItemKind.SUCCESS, reason="")
        assert result.kind == ResolveItemKind.SUCCESS
        assert result.reason == ""

    def test_security_with_a_reason_round_trips(self) -> None:
        result = ResolveItemResult(kind=ResolveItemKind.SECURITY, reason="not a manager")
        assert result.kind == ResolveItemKind.SECURITY
        assert result.reason == "not a manager"

    def test_kind_rejects_values_outside_the_closed_set(self) -> None:
        """``kind`` is constrained to the five documented channels — no ad hoc strings."""
        with pytest.raises(ValidationError):
            ResolveItemResult(kind="admin", reason="")  # type: ignore[arg-type]

    def test_rejects_extra_fields(self) -> None:
        """Unknown wire fields are rejected, not silently ignored — no room for a third field to creep back in."""
        with pytest.raises(ValidationError):
            ResolveItemResult(kind=ResolveItemKind.SUCCESS, reason="", unexpected="value")  # type: ignore[call-arg]

    def test_success_with_a_reason_rejected(self) -> None:
        """Fix-audit finding 7: same kind/reason contract as AccessVerdict, now checked
        on the wire type too, not just the internal one to_wire() copies it from."""
        with pytest.raises(ValidationError, match="kind=SUCCESS"):
            ResolveItemResult(kind=ResolveItemKind.SUCCESS, reason="not empty")

    def test_non_success_with_empty_reason_rejected(self) -> None:
        with pytest.raises(ValidationError, match="kind=SUCCESS"):
            ResolveItemResult(kind=ResolveItemKind.SECURITY, reason="")

    def test_check_error_with_a_reason_round_trips(self) -> None:
        """Unlike AccessVerdict, CHECK_ERROR is an ordinary, valid kind on the wire
        type — the resolver builds it directly, not via to_wire() (fix-audit finding 6:
        no kind gets special-cased beyond the one shared success/reason contract)."""
        result = ResolveItemResult(kind=ResolveItemKind.CHECK_ERROR, reason="UNKNOWN_ENDPOINT")
        assert result.kind == ResolveItemKind.CHECK_ERROR
        assert result.reason == "UNKNOWN_ENDPOINT"


class TestResolveResponse:
    """``ResolveResponse`` — the resolver's response body."""

    def test_results_preserve_order(self) -> None:
        """Results round-trip in the order they were given, matching request items positionally."""
        response = ResolveResponse(
            version=1,
            results=[
                ResolveItemResult(kind=ResolveItemKind.SUCCESS, reason=""),
                ResolveItemResult(kind=ResolveItemKind.SECURITY, reason="not a manager"),
            ],
        )
        assert [r.kind for r in response.results] == [ResolveItemKind.SUCCESS, ResolveItemKind.SECURITY]

    def test_rejects_extra_fields(self) -> None:
        """Unknown top-level wire fields are rejected."""
        with pytest.raises(ValidationError):
            ResolveResponse(version=1, results=[], unexpected="value")  # type: ignore[call-arg]


class TestSupportedVersion:
    """``SUPPORTED_VERSION`` — the single source both the resolver and the manifest read."""

    def test_is_the_draft_v1(self) -> None:
        assert SUPPORTED_VERSION == 1


class TestErrorEnvelope:
    """``ErrorEnvelope`` — the whole-request-failure body, ``{"error": {"code": ...}}``."""

    def test_round_trips_a_code(self) -> None:
        envelope = ErrorEnvelope(error=ErrorDetail(code="unsupported_version"))
        assert envelope.model_dump() == {"error": {"code": "unsupported_version"}}

    def test_code_is_required(self) -> None:
        with pytest.raises(ValidationError):
            ErrorDetail()  # type: ignore[call-arg]

    def test_error_is_required(self) -> None:
        with pytest.raises(ValidationError):
            ErrorEnvelope()  # type: ignore[call-arg]

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError):
            ErrorEnvelope(error=ErrorDetail(code="unsupported_version"), unexpected="value")  # type: ignore[call-arg]
