# tests/adapters/test_base_route_record.py
"""
Tests for BaseRouteRecord and extract_action_types.

BaseRouteRecord is an abstract frozen dataclass that stores the configuration
of one adapter route. It cannot be instantiated directly — only through concrete
subclasses (FastApiRouteRecord, McpRouteRecord). It validates action_class,
extracts generic parameters P and R from BaseAction[P, R], and enforces mapper
invariants (params_mapper required when request_model differs from params_type).

extract_action_types walks the MRO of an action class, finds BaseAction[P, R]
in __orig_bases__, and resolves ForwardRef arguments when needed.

Scenarios covered:
    - Direct instantiation of BaseRouteRecord raises TypeError.
    - Non-BaseAction action_class raises TypeError.
    - Successful type extraction for concrete generics.
    - Successful type extraction for ForwardRef (nested Params/Result).
    - params_type and result_type properties return extracted types.
    - effective_request_model falls back to params_type when request_model is None.
    - effective_response_model falls back to result_type when response_model is None.
    - Missing params_mapper with different request_model raises ValueError.
    - Missing response_mapper with different response_model raises ValueError.
    - Mapper present — no error even with different models.
    - Same request_model as params_type — no mapper needed.
    - ensure_machine_params / ensure_protocol_response raise TypeError on wrong types.
"""

from dataclasses import dataclass

import pytest
from pydantic import BaseModel

from action_machine.adapters.base_route_record import (
    BaseRouteRecord,
    ensure_machine_params,
    ensure_protocol_response,
    extract_action_types,
)
from action_machine.model.base_params import BaseParams
from action_machine.model.base_result import BaseResult
from tests.scenarios.domain_model import FullAction, PingAction, SimpleAction

# ─────────────────────────────────────────────────────────────────────────────
# Minimal concrete subclass — needed because BaseRouteRecord cannot be
# instantiated directly. This subclass adds no extra fields.
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class _TestRouteRecord(BaseRouteRecord):
    """Concrete route record with no protocol-specific fields."""
    pass


# ─────────────────────────────────────────────────────────────────────────────
# Intentionally broken actions for edge-case tests.
# These do NOT belong to the shared domain model.
# ─────────────────────────────────────────────────────────────────────────────


class _NotAnAction:
    """A plain class that is not a BaseAction subclass."""
    pass


class _AltRequest(BaseModel):
    """Alternative request model differing from any action's Params."""
    query: str = "test"


class _AltResponse(BaseModel):
    """Alternative response model differing from any action's Result."""
    data: str = "ok"


# ═════════════════════════════════════════════════════════════════════════════
# Direct instantiation guard
# ═════════════════════════════════════════════════════════════════════════════


class TestDirectInstantiation:
    """Verify that BaseRouteRecord itself cannot be created."""

    def test_raises_type_error(self) -> None:
        """Attempting to create BaseRouteRecord directly raises TypeError."""
        with pytest.raises(TypeError, match="BaseRouteRecord"):
            BaseRouteRecord(action_class=PingAction)


# ═════════════════════════════════════════════════════════════════════════════
# action_class validation
# ═════════════════════════════════════════════════════════════════════════════


class TestActionClassValidation:
    """Verify action_class must be a BaseAction subclass."""

    def test_non_action_raises_type_error(self) -> None:
        """Passing a class that does not inherit BaseAction raises TypeError."""
        with pytest.raises(TypeError, match="BaseAction"):
            _TestRouteRecord(action_class=_NotAnAction)

    def test_string_raises_type_error(self) -> None:
        """Passing a string instead of a class raises TypeError."""
        with pytest.raises(TypeError):
            _TestRouteRecord(action_class="PingAction")  # type: ignore[arg-type]

    def test_valid_action_accepted(self) -> None:
        """A proper BaseAction subclass is accepted without error."""
        record = _TestRouteRecord(action_class=PingAction)
        assert record.action_class is PingAction


# ═════════════════════════════════════════════════════════════════════════════
# Type extraction (extract_action_types)
# ═════════════════════════════════════════════════════════════════════════════


class TestTypeExtraction:
    """Verify that P and R are correctly extracted from BaseAction[P, R]."""

    def test_ping_action_types(self) -> None:
        """PingAction uses ForwardRef — types are resolved to nested classes."""
        p_type, r_type = extract_action_types(PingAction)
        assert p_type is PingAction.Params
        assert r_type is PingAction.Result

    def test_full_action_types(self) -> None:
        """FullAction uses ForwardRef — types are resolved to nested classes."""
        p_type, r_type = extract_action_types(FullAction)
        assert p_type is FullAction.Params
        assert r_type is FullAction.Result

    def test_simple_action_types(self) -> None:
        """SimpleAction uses ForwardRef — types are resolved correctly."""
        p_type, r_type = extract_action_types(SimpleAction)
        assert p_type is SimpleAction.Params
        assert r_type is SimpleAction.Result

    def test_non_action_raises(self) -> None:
        """Calling extract_action_types on a non-action raises TypeError."""
        with pytest.raises(TypeError, match="generic"):
            extract_action_types(_NotAnAction)


# ═════════════════════════════════════════════════════════════════════════════
# Computed properties
# ═════════════════════════════════════════════════════════════════════════════


class TestComputedProperties:
    """Verify params_type, result_type, effective_request/response_model."""

    def test_params_type(self) -> None:
        """params_type returns the extracted P from BaseAction[P, R]."""
        record = _TestRouteRecord(action_class=PingAction)
        assert record.params_type is PingAction.Params

    def test_result_type(self) -> None:
        """result_type returns the extracted R from BaseAction[P, R]."""
        record = _TestRouteRecord(action_class=PingAction)
        assert record.result_type is PingAction.Result

    def test_effective_request_model_defaults_to_params_type(self) -> None:
        """When request_model is None, effective_request_model equals params_type."""
        record = _TestRouteRecord(action_class=PingAction)
        assert record.effective_request_model is PingAction.Params

    def test_effective_request_model_uses_override(self) -> None:
        """When request_model is set, effective_request_model returns it."""
        record = _TestRouteRecord(
            action_class=PingAction,
            request_model=PingAction.Params,  # same type — no mapper needed
        )
        assert record.effective_request_model is PingAction.Params

    def test_effective_response_model_defaults_to_result_type(self) -> None:
        """When response_model is None, effective_response_model equals result_type."""
        record = _TestRouteRecord(action_class=PingAction)
        assert record.effective_response_model is PingAction.Result

    def test_effective_response_model_uses_override(self) -> None:
        """When response_model is set, effective_response_model returns it."""
        record = _TestRouteRecord(
            action_class=PingAction,
            response_model=PingAction.Result,  # same type — no mapper needed
        )
        assert record.effective_response_model is PingAction.Result


# ═════════════════════════════════════════════════════════════════════════════
# Mapper invariants
# ═════════════════════════════════════════════════════════════════════════════


class TestMapperInvariants:
    """Verify that mappers are required when models differ from action types."""

    def test_different_request_model_without_mapper_raises(self) -> None:
        """request_model != params_type and no params_mapper → ValueError."""
        with pytest.raises(ValueError, match="params_mapper"):
            _TestRouteRecord(
                action_class=PingAction,
                request_model=_AltRequest,
            )

    def test_different_response_model_without_mapper_raises(self) -> None:
        """response_model != result_type and no response_mapper → ValueError."""
        with pytest.raises(ValueError, match="response_mapper"):
            _TestRouteRecord(
                action_class=PingAction,
                response_model=_AltResponse,
            )

    def test_different_request_model_with_mapper_accepted(self) -> None:
        """Providing params_mapper resolves the invariant — no error."""
        record = _TestRouteRecord(
            action_class=PingAction,
            request_model=_AltRequest,
            params_mapper=lambda r: PingAction.Params(),
        )
        assert record.effective_request_model is _AltRequest

    def test_different_response_model_with_mapper_accepted(self) -> None:
        """Providing response_mapper resolves the invariant — no error."""
        record = _TestRouteRecord(
            action_class=PingAction,
            response_model=_AltResponse,
            response_mapper=lambda r: _AltResponse(data="mapped"),
        )
        assert record.effective_response_model is _AltResponse

    def test_same_request_model_needs_no_mapper(self) -> None:
        """When request_model is the same type as params_type, no mapper is needed."""
        record = _TestRouteRecord(
            action_class=PingAction,
            request_model=PingAction.Params,
        )
        assert record.params_mapper is None

    def test_none_request_model_needs_no_mapper(self) -> None:
        """When request_model is None (default), no mapper is needed."""
        record = _TestRouteRecord(action_class=PingAction)
        assert record.params_mapper is None


# ═════════════════════════════════════════════════════════════════════════════
# Frozen immutability
# ═════════════════════════════════════════════════════════════════════════════


class TestFrozen:
    """Verify that route records are truly frozen after creation."""

    def test_cannot_set_action_class(self) -> None:
        """Attempting to modify a field on a frozen dataclass raises an error."""
        record = _TestRouteRecord(action_class=PingAction)

        with pytest.raises(AttributeError):
            record.action_class = SimpleAction  # type: ignore[misc]


# ═════════════════════════════════════════════════════════════════════════════
# Runtime mapper output guards (used by FastAPI / MCP adapters)
# ═════════════════════════════════════════════════════════════════════════════


class _ProbeParams(BaseParams):
    pass


class _NotParams:
    pass


class TestMapperOutputGuards:
    """ensure_* helpers reject wrong runtime types at the adapter boundary."""

    def test_ensure_machine_params_ok(self) -> None:
        ensure_machine_params(_ProbeParams(), _ProbeParams, adapter="Test", route_label="x")

    def test_ensure_machine_params_raises(self) -> None:
        with pytest.raises(TypeError, match="params must be an instance"):
            ensure_machine_params(_NotParams(), _ProbeParams, adapter="Test", route_label="route")

    def test_ensure_protocol_response_ok(self) -> None:
        ensure_protocol_response(BaseResult(), BaseResult, adapter="Test", route_label="x")

    def test_ensure_protocol_response_raises(self) -> None:
        with pytest.raises(TypeError, match="response_mapper must return"):
            ensure_protocol_response(_NotParams(), BaseResult, adapter="Test", route_label="route")
