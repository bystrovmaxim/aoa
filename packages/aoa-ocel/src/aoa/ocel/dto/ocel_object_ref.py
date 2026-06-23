# packages/aoa-ocel/src/aoa/ocel/dto/ocel_object_ref.py
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class OcelObjectRef:
    """Event-to-object reference (events[].relationships entry)."""

    object_id: str
    qualifier: str
