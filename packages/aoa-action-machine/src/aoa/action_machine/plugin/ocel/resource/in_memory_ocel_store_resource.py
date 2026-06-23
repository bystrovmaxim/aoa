# packages/aoa-action-machine/src/aoa/action_machine/plugin/ocel/resource/in_memory_ocel_store_resource.py
"""InMemoryOcelStoreResource — in-memory OCEL 2.0 backend."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from aoa.action_machine.exceptions.connection_already_open_error import ConnectionAlreadyOpenError
from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
from aoa.action_machine.plugin.ocel.dto.ocel_event import OcelEvent
from aoa.action_machine.plugin.ocel.dto.ocel_object import OcelObject
from aoa.action_machine.plugin.ocel.exceptions.ocel_contract_error import OcelContractError
from aoa.action_machine.plugin.ocel.resource.ocel_store_resource import OcelStoreResource


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
class InMemoryOcelStoreResource(OcelStoreResource):
    """In-memory backend that writes OCEL 2.0 JSON on ``close()``."""

    def __init__(self, output_file: Path) -> None:
        self._output_file = output_file
        self._lock = asyncio.Lock()
        self._open = False
        self._events: list[OcelEvent] = []
        self._objects: dict[str, OcelObject] = {}
        self._event_ids: set[str] = set()

    async def open(self) -> None:
        async with self._lock:
            if self._open:
                raise ConnectionAlreadyOpenError("InMemoryOcelStoreResource is already open.")
            self._open = True

    async def close(self) -> None:
        async with self._lock:
            if not self._open:
                return
            await self._write_locked()
            self._open = False

    async def add_event(self, event: OcelEvent) -> None:
        async with self._lock:
            self._assert_open()
            if event.id in self._event_ids:
                raise OcelContractError(f"Duplicate OcelEvent.id: {event.id}")
            self._event_ids.add(event.id)
            self._events.append(event)
            for obj_fact in event.objects:
                self._merge_object_fact(obj_fact)

    def _assert_open(self) -> None:
        if not self._open:
            raise OcelContractError("Resource is not open. Call await resource.open() first.")

    def _merge_object_fact(self, incoming: OcelObject) -> None:
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
        doc = self._materialize()
        self._output_file.parent.mkdir(parents=True, exist_ok=True)
        self._output_file.write_text(
            json.dumps(doc, ensure_ascii=False, indent=2, default=self._json_default),
            encoding="utf-8",
        )

    @staticmethod
    def _json_default(obj: Any) -> Any:
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

    def _materialize(self) -> dict[str, Any]:
        return {
            "eventTypes": self._derive_event_types(),
            "objectTypes": self._derive_object_types(),
            "events": [self._serialize_event(ev) for ev in self._events],
            "objects": [self._serialize_object(obj) for obj in sorted(self._objects.values(), key=lambda o: o.id)],
        }

    def _derive_event_types(self) -> list[dict[str, Any]]:
        type_attrs: dict[str, dict[str, str]] = {}
        for ev in self._events:
            type_attrs.setdefault(ev.type, {})
            for attr in ev.attributes:
                if attr.name not in type_attrs[ev.type]:
                    type_attrs[ev.type][attr.name] = _infer_ocel_type(attr.value)
        return _type_catalog(type_attrs)

    def _derive_object_types(self) -> list[dict[str, Any]]:
        type_attrs: dict[str, dict[str, str]] = {}
        for obj in self._objects.values():
            type_attrs.setdefault(obj.type, {})
            for attr in obj.attributes:
                if attr.name not in type_attrs[obj.type]:
                    type_attrs[obj.type][attr.name] = _infer_ocel_type(attr.value)
        return _type_catalog(type_attrs)

    def _serialize_event(self, ev: OcelEvent) -> dict[str, Any]:
        return {
            "id": ev.id,
            "type": ev.type,
            "time": ev.time.isoformat(),
            "attributes": [{"name": a.name, "value": self._serialize_attr_value(a.value)} for a in ev.attributes],
            "relationships": [{"objectId": r.object_id, "qualifier": r.qualifier} for r in ev.relationships],
        }

    def _serialize_object(self, obj: OcelObject) -> dict[str, Any]:
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
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value
        if value is None:
            return None
        return str(value)
