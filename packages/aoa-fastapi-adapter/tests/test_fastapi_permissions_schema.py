# tests/test_fastapi_permissions_schema.py
"""
Tests for ``aoa.fastapi.permissions_schema`` — ``/permissions/resolve`` wire models (issue #130).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Validate required/default fields, the non-empty ``items`` invariant, extra-field
rejection, and that every ``BaseVerdict`` subclass is exactly its own flat shape —
``AllowedVerdict`` with no ``reason`` at all, ``FailSecurityVerdict``/
``FailErrorVerdict`` with ``reason`` mandatory and non-empty.
"""

import pytest
from pydantic import ValidationError

from aoa.action_machine.intents.access_control import AllowedVerdict, FailErrorVerdict, FailSecurityVerdict
from aoa.fastapi.permissions_schema import (
    SUPPORTED_VERSION,
    ErrorDetail,
    ErrorEnvelope,
    ResolveItem,
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


class TestBaseVerdictSubclasses:
    """``AllowedVerdict``/``FailSecurityVerdict``/``FailErrorVerdict`` — one class per
    outcome, ``kind`` computed from the class name, never a free field."""

    def test_allowed_verdict_has_no_reason_field(self) -> None:
        """AllowedVerdict carries no reason at all -- not an empty one, none."""
        assert AllowedVerdict().kind == "AllowedVerdict"
        with pytest.raises(ValidationError):
            AllowedVerdict(reason="")  # type: ignore[call-arg]

    def test_fail_security_verdict_requires_a_non_empty_reason(self) -> None:
        with pytest.raises(ValidationError):
            FailSecurityVerdict("")

    def test_fail_security_verdict_round_trips(self) -> None:
        result = FailSecurityVerdict("not a manager")
        assert result.kind == "FailSecurityVerdict"
        assert result.reason == "not a manager"

    def test_fail_error_verdict_round_trips(self) -> None:
        """FailErrorVerdict is its own class, not a value of some shared kind field --
        the resolver builds it directly for e.g. UNKNOWN_ENDPOINT, never a
        FailSecurityVerdict (fix-audit finding 6: no kind gets special-cased beyond
        the one shared per-class reason contract)."""
        result = FailErrorVerdict("UNKNOWN_ENDPOINT")
        assert result.kind == "FailErrorVerdict"
        assert result.reason == "UNKNOWN_ENDPOINT"

    def test_rejects_extra_fields(self) -> None:
        """Unknown wire fields are rejected, not silently ignored."""
        with pytest.raises(ValidationError):
            FailSecurityVerdict.model_validate({"reason": "not a manager", "unexpected": "value"})


class TestResolveResponse:
    """``ResolveResponse`` — the resolver's response body."""

    def test_results_preserve_order(self) -> None:
        """Results round-trip in the order they were given, matching request items positionally."""
        response = ResolveResponse(
            version=1,
            results=[AllowedVerdict(), FailSecurityVerdict("not a manager")],
        )
        assert [r.kind for r in response.results] == ["AllowedVerdict", "FailSecurityVerdict"]

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
