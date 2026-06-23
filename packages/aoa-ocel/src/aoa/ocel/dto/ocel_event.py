# packages/aoa-ocel/src/aoa/ocel/dto/ocel_event.py
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from aoa.ocel.dto.ocel_attribute import OcelAttribute
from aoa.ocel.dto.ocel_object import OcelObject
from aoa.ocel.dto.ocel_object_ref import OcelObjectRef


@dataclass(slots=True)
class OcelEvent:
    """Composite event record passed to ``OcelStoreResource.add_event()``.

    DTO graph (maps to OCEL 2.0 ``events[]`` + embedded ``objects[]`` facts)::

        OcelEvent
        ├── id: str
        ├── type: str                          → eventTypes[].name
        ├── time: datetime                     → events[].time (UTC)
        │
        ├── attributes: list[OcelAttribute]
        │       OcelAttribute
        │       ├── name: str
        │       └── value: Any                 → static; no ``time`` field
        │
        ├── relationships: list[OcelObjectRef]   → E2O (event → object)
        │       OcelObjectRef
        │       ├── object_id: str             → target ``OcelObject.id``
        │       └── qualifier: str
        │
        └── objects: list[OcelObject]          → objects[] section
                OcelObject
                ├── id: str
                ├── type: str                  → objectTypes[].name
                │
                └── attributes: list[OcelAttribute]
                        └── static object attrs (scalars / lifecycle snapshot)

    v1 builder policy (E2O only): ``relationships`` are built from ``OcelFrame`` rows
    plus one-hop **loaded** relation peers on each ``frame.object``; composite
    peer qualifier ``{frame.qualifier}.{field_name}``. No O2O export; see
    ``packages/aoa-ocel/src/aoa/ocel/README.md`` — **Export policy (v1)**.

    AI-CORE-BEGIN
    ROLE: Single composite payload for one ``OcelStoreResource.add_event()`` call.
    CONTRACT: ``relationships`` are E2O rows; ``objects`` materialize root and one-hop loaded peers.
    INVARIANTS: ``time`` is UTC-aware before persist; attribute values are JSON-serializable primitives (plugin builds DTOs).
    AI-CORE-END
    """

    id: str
    type: str
    time: datetime
    attributes: list[OcelAttribute] = field(default_factory=list)
    relationships: list[OcelObjectRef] = field(default_factory=list)
    objects: list[OcelObject] = field(default_factory=list)
