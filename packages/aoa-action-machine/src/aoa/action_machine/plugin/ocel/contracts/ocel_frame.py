# packages/aoa-action-machine/src/aoa/action_machine/plugin/ocel/contracts/ocel_frame.py
"""
OcelFrame[T] — explicit contract container for OCEL serialization.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Aspects declare which domain object anchors an export row and the E2O role
(``qualifier``) for the root. The future builder adds E2O for **loaded**
one-hop relation peers on ``frame.object`` without separate frames.

Full export rules (E2O-only v1, loaded FK, one hop, analytics trade-off):
``packages/aoa-action-machine/src/aoa/action_machine/plugin/ocel/README.md`` — section **Export policy (v1)**.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    aspect loads relations on entity → OcelFrame(object, qualifier, attributes?)
              │
              ▼
    builder (PR-7): root E2O + one-hop loaded FK → E2O with "{qualifier}.{field}"
              │
              ▼
    OcelEvent → OcelStoreResource
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TypeVar

from aoa.action_machine.domain.entity import BaseEntity
from aoa.action_machine.plugin.ocel.dto.ocel_attribute import OcelAttribute
from aoa.action_machine.plugin.ocel.exceptions.ocel_contract_error import OcelContractError

T = TypeVar("T", bound=BaseEntity)


@dataclass(frozen=True)
class OcelFrame[T: BaseEntity]:
    """Explicit contract that an aspect returns for OCEL serialization.

    Builder mapping (v1, see package README)::

        OcelFrame
        ├── object ──────────────────────► E2O (qualifier = frame.qualifier)
        │   └── loaded FK peers (1 hop) ► E2O (qualifier = "{frame.qualifier}.{field}")
        └── attributes ──────────────────► OcelPlugin merges → OcelEvent.attributes

    Loaded-only rule: only ``get_foreign_keys(loaded_only=True)`` on ``object``;
    undeclared DB relations and scalar ``*_id`` columns are not E2O.

    AI-CORE-BEGIN
    ROLE: Root participation row; builder derives secondary E2O from loaded one-hop relations on ``object``.
    CONTRACT: ``object``, non-empty ``qualifier``, optional ``attributes``; multiple frames per trace allowed.
    INVARIANTS: ``qualifier`` is non-empty; zero frames in finish snapshots → no OCEL write; v1 exports E2O only (no O2O); attribute merge is ``OcelPlugin`` policy on ``GlobalFinishEvent.all_aspect_states``.
    AI-CORE-END

    Example — one frame; patient loaded, clinic not loaded::

        OcelFrame(
            object=doctor,  # patient relation loaded; clinic relation not loaded
            qualifier="Signed prescription",
            attributes=[OcelAttribute(name="channel", value="electronic")],
        )
        # builder E2O: doctor ("Signed prescription"), patient ("Signed prescription.patient")
    """

    object: T
    qualifier: str
    attributes: list[OcelAttribute] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.qualifier.strip():
            raise OcelContractError("OcelFrame.qualifier must be non-empty")
