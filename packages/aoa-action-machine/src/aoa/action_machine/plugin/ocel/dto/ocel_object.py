# packages/aoa-action-machine/src/aoa/action_machine/plugin/ocel/dto/ocel_object.py
from __future__ import annotations

from dataclasses import dataclass, field

from aoa.action_machine.plugin.ocel.dto.ocel_attribute import OcelAttribute
from aoa.action_machine.plugin.ocel.dto.ocel_object_relationship import OcelObjectRelationship


@dataclass(slots=True)
class OcelObject:
    """Full object entry for materializing the objects section."""

    id: str
    type: str
    attributes: list[OcelAttribute] = field(default_factory=list)
    relationships: list[OcelObjectRelationship] = field(default_factory=list)
