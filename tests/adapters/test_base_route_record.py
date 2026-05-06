# tests/adapters/test_base_route_record.py
"""
Unit tests for ``BaseRouteRecord`` and ``extract_action_types``.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Exercise the frozen route-record contract: ``action_class`` validation, generic
``P``/``R`` extraction via ``extract_action_types`` (including ``ForwardRef`` paths;
non-actions surface :exc:`ValueError` from schema resolution),
``effective_*_model`` fallbacks, mapper invariants, immutability, and the
``ensure_machine_params`` / ``ensure_protocol_response`` guards used at adapter
boundaries.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    Action class (scenario or local broken fixture)
              |
              v
    _TestRouteRecord(BaseRouteRecord)  OR  extract_action_types(cls)
              |
              +--> params_type / result_type (from ``__orig_bases__``)
              |
              +--> effective_request_model / effective_response_model
              |         (override vs extracted + mapper rules)
              |
              v
    ensure_* (runtime)  — validate instances before/after ``machine.run``

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- ``BaseRouteRecord`` cannot be instantiated directly; only concrete subclasses.
- ``action_class`` must be a ``BaseAction`` subclass before type extraction.
- Diverging ``request_model`` / ``response_model`` requires matching mappers.

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
# Minimal concrete subclass — ``BaseRouteRecord`` cannot be instantiated
# directly. This subclass adds no protocol-specific fields.
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class _TestRouteRecord(BaseRouteRecord):
    """Concrete route record with no transport-specific fields."""
    pass


# ─────────────────────────────────────────────────────────────────────────────
# Intentionally broken actions for edge-case tests (not in shared domain).
# ─────────────────────────────────────────────────────────────────────────────


class _NotAnAction:
    """Plain class that is not a ``BaseAction`` subclass."""
    pass


class _AltRequest(BaseModel):
    """Alternative request model differing from the action's ``Params``."""
    query: str = "test"


class _AltResponse(BaseModel):
    """Alternative response model differing from the action's ``Result``."""
    data: str = "ok"


# ═════════════════════════════════════════════════════════════════════════════
# Direct instantiation guard
# ═════════════════════════════════════════════════════════════════════════════


class TestDirectInstantiation:
    """``BaseRouteRecord`` itself must not be constructible."""

    def test_raises_type_error(self) -> None:
        """Direct ``BaseRouteRecord(...)`` raises ``TypeError``."""
        with pytest.raises(TypeError, match="BaseRouteRecord"):
            BaseRouteRecord(action_class=PingAction)


# ═════════════════════════════════════════════════════════════════════════════
# action_class validation
# ═════════════════════════════════════════════════════════════════════════════


class TestActionClassValidation:
    """``action_class`` must be a ``BaseAction`` subclass."""

    def test_non_action_raises_type_error(self) -> None:
        """Non-``BaseAction`` class raises ``TypeError``."""
        with pytest.raises(TypeError, match="BaseAction"):
            _TestRouteRecord(action_class=_NotAnAction)

    def test_string_raises_type_error(self) -> None:
        """A string is not a valid ``action_class``."""
        with pytest.raises(TypeError):
            _TestRouteRecord(action_class="PingAction")  # type: ignore[arg-type]

    def test_valid_action_accepted(self) -> None:
        """A proper ``BaseAction`` subclass is accepted."""
        record = _TestRouteRecord(action_class=PingAction)
        assert record.action_class is PingAction


# ═════════════════════════════════════════════════════════════════════════════
# Type extraction (``extract_action_types``)
# ═════════════════════════════════════════════════════════════════════════════


class TestTypeExtraction:
    """``P`` and ``R`` resolved from ``BaseAction[P, R]`` (incl. ``ForwardRef``)."""

    def test_ping_action_types(self) -> None:
        """``PingAction`` nested ``Params``/``Result`` resolve correctly."""
        p_type, r_type = extract_action_types(PingAction)
        assert p_type is PingAction.Params
        assert r_type is PingAction.Result

    def test_full_action_types(self) -> None:
        """``FullAction`` nested types resolve correctly."""
        p_type, r_type = extract_action_types(FullAction)
        assert p_type is FullAction.Params
        assert r_type is FullAction.Result

    def test_simple_action_types(self) -> None:
        """``SimpleAction`` nested types resolve correctly."""
        p_type, r_type = extract_action_types(SimpleAction)
        assert p_type is SimpleAction.Params
        assert r_type is SimpleAction.Result

    def test_non_action_extract_raises_value_error(self) -> None:
        """``extract_action_types`` on a plain class triggers resolver ``ValueError``."""
        with pytest.raises(ValueError, match="Failed to resolve params type"):
            extract_action_types(_NotAnAction)


# ═════════════════════════════════════════════════════════════════════════════
# Computed properties
# ═════════════════════════════════════════════════════════════════════════════


class TestComputedProperties:
    """``params_type``, ``result_type``, ``effective_*_model``."""

    def test_params_type(self) -> None:
        """``params_type`` is extracted ``P``."""
        record = _TestRouteRecord(action_class=PingAction)
        assert record.params_type is PingAction.Params

    def test_result_type(self) -> None:
        """``result_type`` is extracted ``R``."""
        record = _TestRouteRecord(action_class=PingAction)
        assert record.result_type is PingAction.Result

    def test_effective_request_model_defaults_to_params_type(self) -> None:
        """``request_model is None`` → ``effective_request_model`` is ``params_type``."""
        record = _TestRouteRecord(action_class=PingAction)
        assert record.effective_request_model is PingAction.Params

    def test_effective_request_model_uses_override(self) -> None:
        """Explicit ``request_model`` (same as ``params_type``) is reflected."""
        record = _TestRouteRecord(
            action_class=PingAction,
            request_model=PingAction.Params,
        )
        assert record.effective_request_model is PingAction.Params

    def test_effective_response_model_defaults_to_result_type(self) -> None:
        """``response_model is None`` → ``effective_response_model`` is ``result_type``."""
        record = _TestRouteRecord(action_class=PingAction)
        assert record.effective_response_model is PingAction.Result

    def test_effective_response_model_uses_override(self) -> None:
        """Explicit ``response_model`` (same as ``result_type``) is reflected."""
        record = _TestRouteRecord(
            action_class=PingAction,
            response_model=PingAction.Result,
        )
        assert record.effective_response_model is PingAction.Result


# ═════════════════════════════════════════════════════════════════════════════
# Mapper invariants
# ═════════════════════════════════════════════════════════════════════════════


class TestMapperInvariants:
    """Mappers required when protocol models differ from action types."""

    def test_different_request_model_without_mapper_raises(self) -> None:
        """``request_model != params_type`` without ``params_mapper`` → ``ValueError``."""
        with pytest.raises(ValueError, match="params_mapper"):
            _TestRouteRecord(
                action_class=PingAction,
                request_model=_AltRequest,
            )

    def test_different_response_model_without_mapper_raises(self) -> None:
        """``response_model != result_type`` without ``response_mapper`` → ``ValueError``."""
        with pytest.raises(ValueError, match="response_mapper"):
            _TestRouteRecord(
                action_class=PingAction,
                response_model=_AltResponse,
            )

    def test_different_request_model_with_mapper_accepted(self) -> None:
        """``params_mapper`` satisfies the request-side invariant."""
        record = _TestRouteRecord(
            action_class=PingAction,
            request_model=_AltRequest,
            params_mapper=lambda r: PingAction.Params(),
        )
        assert record.effective_request_model is _AltRequest

    def test_different_response_model_with_mapper_accepted(self) -> None:
        """``response_mapper`` satisfies the response-side invariant."""
        record = _TestRouteRecord(
            action_class=PingAction,
            response_model=_AltResponse,
            response_mapper=lambda r: _AltResponse(data="mapped"),
        )
        assert record.effective_response_model is _AltResponse

    def test_same_request_model_needs_no_mapper(self) -> None:
        """Same ``request_model`` as ``params_type`` needs no mapper."""
        record = _TestRouteRecord(
            action_class=PingAction,
            request_model=PingAction.Params,
        )
        assert record.params_mapper is None

    def test_none_request_model_needs_no_mapper(self) -> None:
        """Default ``request_model`` needs no mapper."""
        record = _TestRouteRecord(action_class=PingAction)
        assert record.params_mapper is None


# ═════════════════════════════════════════════════════════════════════════════
# Frozen immutability
# ═════════════════════════════════════════════════════════════════════════════


class TestFrozen:
    """Route records are immutable after creation."""

    def test_cannot_set_action_class(self) -> None:
        """Assigning to a frozen field raises."""
        record = _TestRouteRecord(action_class=PingAction)

        with pytest.raises(AttributeError):
            record.action_class = SimpleAction  # type: ignore[misc]


# ═════════════════════════════════════════════════════════════════════════════
# Runtime mapper output guards (FastAPI / MCP adapters)
# ═════════════════════════════════════════════════════════════════════════════


class _ProbeParams(BaseParams):
    pass


class _NotParams:
    pass


class TestMapperOutputGuards:
    """``ensure_*`` reject wrong runtime types at the adapter boundary."""

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
