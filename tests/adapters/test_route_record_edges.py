# tests/adapters/test_route_record_edges.py
"""
Extra coverage for type extraction on ``BaseAction[P, R]`` route records.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Exercises edge branches in ``base_route_record.py``:

- ``_resolve_forward_ref``: failed resolution paths.
- ``_resolve_generic_arg``: string arguments and unknown argument kinds.
- ``effective_request_model`` / ``effective_response_model`` when an explicit
  override differs from the extracted generic args (with mappers present).

Broken or non-standard ``Action`` stand-ins are defined **inside this module**
only — they are not part of the shared scenario domain.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    tests (this module)
              |
              v
    base_route_record._resolve_forward_ref / _resolve_generic_arg
    (called directly — not via public adapter APIs)
              |
              v
    PingAction (scenario anchor)  +  local _TestRecord
              |
              +--> failed ref / odd arg  ->  None
              |
              +--> _TestRecord + mappers  ->  effective_*_model overrides

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- ``action_class`` must be a concrete ``BaseAction`` subclass before type
  extraction helpers run in production; tests call private helpers directly
  with controlled inputs.

"""

from dataclasses import dataclass
from typing import ForwardRef

from pydantic import BaseModel

from action_machine.adapters.base_route_record import (
    BaseRouteRecord,
    _resolve_forward_ref,
    _resolve_generic_arg,
)
from action_machine.model.base_params import BaseParams
from tests.scenarios.domain_model import PingAction

# ─────────────────────────────────────────────────────────────────────────────
# Helpers — non-standard models, not part of the production domain.
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class _TestRecord(BaseRouteRecord):
    """Concrete ``BaseRouteRecord`` for tests."""
    pass


class _AltRequest(BaseModel):
    """Request model distinct from any ``Params`` on the action."""
    query: str = "test"


class _AltResponse(BaseModel):
    """Response model distinct from any ``Result`` on the action."""
    data: str = "ok"


# ═════════════════════════════════════════════════════════════════════════════
# _resolve_forward_ref — failed resolution
# ═════════════════════════════════════════════════════════════════════════════


class TestResolveForwardRef:
    """Fallback branches for ``_resolve_forward_ref``."""

    def test_nonexistent_class_returns_none(self) -> None:
        """A forward ref to a missing class name resolves to ``None``."""
        # Arrange
        ref = ForwardRef("CompletelyNonexistentClassName12345")

        # Act
        result = _resolve_forward_ref(ref, PingAction)

        # Assert
        assert result is None

    def test_non_type_ref_returns_none(self) -> None:
        """Forward ref that resolves to a non-type object (here: module ``__name__`` str) → ``None``."""
        # Arrange — ``__name__`` on the action's module is a ``str``, not a ``type``
        ref = ForwardRef("__name__")

        # Act
        result = _resolve_forward_ref(ref, PingAction)

        # Assert
        assert result is None


# ═════════════════════════════════════════════════════════════════════════════
# _resolve_generic_arg — all branches
# ═════════════════════════════════════════════════════════════════════════════


class TestResolveGenericArg:
    """All branches of ``_resolve_generic_arg``."""

    def test_type_passthrough(self) -> None:
        """A concrete ``type`` is returned unchanged."""
        # Act
        result = _resolve_generic_arg(BaseParams, PingAction)

        # Assert
        assert result is BaseParams

    def test_forward_ref_resolved(self) -> None:
        """``ForwardRef`` resolves against the action class context."""
        # Arrange
        ref = ForwardRef("PingAction.Params")

        # Act
        result = _resolve_generic_arg(ref, PingAction)

        # Assert
        assert result is PingAction.Params

    def test_string_resolved(self) -> None:
        """String arguments are wrapped as ``ForwardRef`` and resolved."""
        # Act
        result = _resolve_generic_arg("PingAction.Result", PingAction)

        # Assert
        assert result is PingAction.Result

    def test_string_nonexistent_returns_none(self) -> None:
        """An unknown string name resolves to ``None``."""
        # Act
        result = _resolve_generic_arg("NoSuchClass999", PingAction)

        # Assert
        assert result is None

    def test_unknown_type_returns_none(self) -> None:
        """Non-type, non-ForwardRef, non-str arguments → ``None``."""
        # Arrange — integer argument
        # Act
        result = _resolve_generic_arg(42, PingAction)

        # Assert
        assert result is None


# ═════════════════════════════════════════════════════════════════════════════
# effective_request_model / effective_response_model with overrides
# ═════════════════════════════════════════════════════════════════════════════


class TestEffectiveModelOverrides:
    """``effective_*_model`` when override types differ (with mappers)."""

    def test_effective_request_with_different_model(self) -> None:
        """``request_model`` wins over extracted ``params_type`` when mappers exist."""
        # Arrange — _AltRequest != PingAction.Params
        record = _TestRecord(
            action_class=PingAction,
            request_model=_AltRequest,
            params_mapper=lambda r: PingAction.Params(),
        )

        # Act
        result = record.effective_request_model

        # Assert
        assert result is _AltRequest

    def test_effective_response_with_different_model(self) -> None:
        """``response_model`` wins over extracted ``result_type`` when mappers exist."""
        # Arrange — _AltResponse != PingAction.Result
        record = _TestRecord(
            action_class=PingAction,
            response_model=_AltResponse,
            response_mapper=lambda r: _AltResponse(data="mapped"),
        )

        # Act
        result = record.effective_response_model

        # Assert
        assert result is _AltResponse
