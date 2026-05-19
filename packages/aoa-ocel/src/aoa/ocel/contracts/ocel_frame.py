# packages/aoa-ocel/src/aoa/ocel/contracts/ocel_frame.py
"""OcelFrame[T] — explicit contract container for OCEL serialization."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeVar

from aoa.action_machine.domain.entity import BaseEntity

T = TypeVar("T", bound=BaseEntity)


@dataclass(frozen=True)
class OcelFrame[T: BaseEntity]:
    """Explicit contract that an aspect returns for OCEL serialization.

    AI-CORE-BEGIN
    ROLE: Carry exactly one root domain entity from an aspect result into OCEL export.
    CONTRACT: Immutable wrapper with a single ``object`` field; discovered in ``GlobalFinishEvent.pipeline_state`` (PR-6).
    INVARIANTS: At most one ``OcelFrame`` per pipeline snapshot; zero frames means no OCEL write; more than one is ``OcelContractError``.
    AI-CORE-END

    Carries exactly one root domain entity. OcelPlugin searches for exactly
    one OcelFrame in GlobalFinishEvent.pipeline_state (PR-6).

    Example usage in an aspect::

        @result_instance("ocel", OcelFrame, required=True, no_none=True)
        async def process_order_aspect(self, params, state, box, connections):
            order = ...  # load or build OrderEntity
            return {"ocel": OcelFrame(object=order)}
    """

    object: T
