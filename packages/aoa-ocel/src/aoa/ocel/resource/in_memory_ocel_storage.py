# packages/aoa-ocel/src/aoa/ocel/resource/in_memory_ocel_storage.py
"""
InMemoryOcelStorage — in-memory OCEL 2.0 backend.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Accumulate OCEL events in memory and persist the complete log when the owner closes the store.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    Owner storage -> nested storage wrapper -> shared OCEL events
"""

from __future__ import annotations

import asyncio
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from aoa.action_machine.exceptions.connection_already_open_error import ConnectionAlreadyOpenError
from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
from aoa.ocel.dto.ocel_event import OcelEvent
from aoa.ocel.dto.ocel_object import OcelObject
from aoa.ocel.exceptions.ocel_contract_error import OcelContractError
from aoa.ocel.resource.ocel_storage import OcelStorage


def _type_catalog(type_attrs: dict[str, dict[str, str]]) -> list[dict[str, Any]]:
    """Build OCEL 2.0 eventTypes/objectTypes JSON from name → {attr: ocel_type}."""
    return [
        {
            "name": type_name,
            "attributes": [
                {"name": attr_name, "type": attr_type} for attr_name, attr_type in sorted(type_attrs[type_name].items())
            ],
        }
        for type_name in sorted(type_attrs)
    ]


def _infer_ocel_type(value: Any) -> str:
    """Classify an attribute for the OCEL type catalog."""
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "float"
    if isinstance(value, datetime):
        return "date"
    return "string"


@exclude_graph_model
class InMemoryOcelStorage(OcelStorage):
    """
    Accumulate events and persist OCEL JSON when the owner closes the store.

    AI-CORE-BEGIN
    ROLE: In-memory OCEL storage with file persistence.
    CONTRACT: Accept events while open and write the accumulated log on close.
    INVARIANTS: Event identities are unique; nested actions cannot control the lifecycle.
    AI-CORE-END
    """

    def __init__(self, output_file: Path) -> None:
        """Prepare an empty store with a persistence destination."""
        self._output_file = output_file
        self._lock = asyncio.Lock()
        self._open = False
        self._events: list[OcelEvent] = []
        self._objects: dict[str, OcelObject] = {}
        self._event_ids: set[str] = set()

    async def open(self) -> None:
        """Begin accepting events into this store."""
        async with self._lock:
            if self._open:
                raise ConnectionAlreadyOpenError("InMemoryOcelStorage is already open.")
            self._open = True

    async def close(self) -> None:
        """Persist accumulated events and end the session."""
        async with self._lock:
            if not self._open:
                return
            await self._write_locked()
            self._open = False

    async def add_event(self, event: OcelEvent) -> None:
        """Accumulate a unique event and its object facts."""
        async with self._lock:
            self._assert_open()
            if event.id in self._event_ids:
                raise OcelContractError(f"Duplicate OcelEvent.id: {event.id}")
            self._event_ids.add(event.id)
            self._events.append(event)
            for obj_fact in event.objects:
                self._merge_object_fact(obj_fact)

    def _assert_open(self) -> None:
        """Require an active session before accepting events."""
        if not self._open:
            raise OcelContractError("Resource is not open. Call await resource.open() first.")

    def _merge_object_fact(self, incoming: OcelObject) -> None:
        """Reconcile an object’s facts across incoming events."""
        if incoming.id not in self._objects:
            self._objects[incoming.id] = OcelObject(
                id=incoming.id,
                type=incoming.type,
                attributes=list(incoming.attributes),
                relationships=list(incoming.relationships),
            )
            return

        existing = self._objects[incoming.id]
        existing_attrs = {a.name: a for a in existing.attributes}
        for attr in incoming.attributes:
            existing_attrs[attr.name] = attr
        existing.attributes = list(existing_attrs.values())

        existing_rels = {(r.object_id, r.qualifier) for r in existing.relationships}
        for rel in incoming.relationships:
            key = (rel.object_id, rel.qualifier)
            if key not in existing_rels:
                existing.relationships.append(rel)
                existing_rels.add(key)

    async def _write_locked(self) -> None:
        """Replace the output file whole, so a reader never sees it half written."""
        text = json.dumps(self._materialize(), ensure_ascii=False, indent=2, default=self._json_default)
        folder = self._output_file.parent
        folder.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=folder, prefix=f".{self._output_file.name}.", suffix=".tmp", delete=False
        ) as staged:
            staged.write(text)
        try:
            os.replace(staged.name, self._output_file)
        except BaseException:
            os.unlink(staged.name)
            raise

    @staticmethod
    def _json_default(obj: Any) -> Any:
        """Encode datetime values for OCEL JSON output."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

    def _materialize(self) -> dict[str, Any]:
        """Assemble the complete OCEL interchange document."""
        return {
            "eventTypes": self._derive_event_types(),
            "objectTypes": self._derive_object_types(),
            "events": [self._serialize_event(ev) for ev in self._events],
            "objects": [self._serialize_object(obj) for obj in sorted(self._objects.values(), key=lambda o: o.id)],
        }

    def _derive_event_types(self) -> list[dict[str, Any]]:
        """Describe attributes observed on each event type."""
        type_attrs: dict[str, dict[str, str]] = {}
        for ev in self._events:
            type_attrs.setdefault(ev.type, {})
            for attr in ev.attributes:
                if attr.name not in type_attrs[ev.type]:
                    type_attrs[ev.type][attr.name] = _infer_ocel_type(attr.value)
        return _type_catalog(type_attrs)

    def _derive_object_types(self) -> list[dict[str, Any]]:
        """Describe attributes observed on each object type."""
        type_attrs: dict[str, dict[str, str]] = {}
        for obj in self._objects.values():
            type_attrs.setdefault(obj.type, {})
            for attr in obj.attributes:
                if attr.name not in type_attrs[obj.type]:
                    type_attrs[obj.type][attr.name] = _infer_ocel_type(attr.value)
        return _type_catalog(type_attrs)

    def _serialize_event(self, ev: OcelEvent) -> dict[str, Any]:
        """Express an event in the OCEL interchange shape."""
        return {
            "id": ev.id,
            "type": ev.type,
            "time": ev.time.isoformat(),
            "attributes": [{"name": a.name, "value": self._serialize_attr_value(a.value)} for a in ev.attributes],
            "relationships": [{"objectId": r.object_id, "qualifier": r.qualifier} for r in ev.relationships],
        }

    def _serialize_object(self, obj: OcelObject) -> dict[str, Any]:
        """Express an object in the OCEL interchange shape."""
        attrs_out: list[dict[str, Any]] = []
        for attr in sorted(obj.attributes, key=lambda a: a.name):
            attrs_out.append({"name": attr.name, "value": self._serialize_attr_value(attr.value)})
        return {
            "id": obj.id,
            "type": obj.type,
            "attributes": attrs_out,
            "relationships": [
                {"objectId": r.object_id, "qualifier": r.qualifier}
                for r in sorted(obj.relationships, key=lambda r: (r.object_id, r.qualifier))
            ],
        }

    @staticmethod
    def _serialize_attr_value(value: Any) -> Any:
        """Normalize an attribute value for OCEL interchange."""
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value
        if value is None:
            return None
        return str(value)
