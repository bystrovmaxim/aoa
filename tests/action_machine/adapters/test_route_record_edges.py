# tests/adapters/test_route_record_edges.py
"""
Extra coverage for type extraction on ``BaseAction[P, R]`` route records.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Exercises edge branches around route-record type extraction:

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
    PingAction (scenario anchor)  +  local _TestRecord
              |
              +--> _TestRecord + mappers  ->  effective_*_model overrides

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- ``action_class`` must be a concrete ``BaseAction`` subclass before type
  extraction runs in production.

"""

from dataclasses import dataclass

from pydantic import BaseModel

from aoa.action_machine.adapters.base_route_record import (
    BaseRouteRecord,
)
from tests.action_machine.scenarios.domain_model import PingAction

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
