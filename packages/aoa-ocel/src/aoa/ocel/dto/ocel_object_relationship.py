# packages/aoa-ocel/src/aoa/ocel/dto/ocel_object_relationship.py
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class OcelObjectRelationship:
    """Object-to-object relationship derived from a relation container field."""

    object_id: str
    qualifier: str
