# packages/aoa-ocel/src/aoa/ocel/plugin/ocel_plugin.py
"""
OcelPlugin — OCEL 2.0 export on ``GlobalFinishEvent``.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Read ``OcelFrame`` rows from ``GlobalFinishEvent.all_aspect_states`` (and
optional frames on ``result``), build one ``OcelEvent`` (E2O-only v1), append via
``OcelStoreProtocol.add_event``. Does not mutate pipeline state or the event.

Export policy: ``packages/aoa-ocel/src/aoa/ocel/README.md`` — **Export policy (v1)**.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from typing import Annotated, Any, Union, get_args, get_origin

from aoa.action_machine.domain.entity import BaseEntity
from aoa.action_machine.domain.relation_containers import BaseRelationMany, BaseRelationOne
from aoa.action_machine.intents.on import GlobalFinishEvent, on
from aoa.action_machine.plugin.core import Plugin
from aoa.ocel.contracts.ocel_frame import OcelFrame
from aoa.ocel.dto.ocel_attribute import OcelAttribute
from aoa.ocel.dto.ocel_event import OcelEvent
from aoa.ocel.dto.ocel_object import OcelObject
from aoa.ocel.dto.ocel_object_ref import OcelObjectRef
from aoa.ocel.exceptions.ocel_contract_error import OcelContractError
from aoa.ocel.resource.ocel_store_protocol import OcelStoreProtocol
from aoa.ocel.type_id import make_oid

OCEL_FRAMES_KEY = "ocel_frames"
_OCEL_TYPE_SUFFIXES = ("Action", "Entity", "Lifecycle")


class OcelPlugin(Plugin):
    """
    AI-CORE-BEGIN
    ROLE: On ``GlobalFinishEvent``, scan ``all_aspect_states`` for ``OcelFrame`` rows and write one ``OcelEvent``.
    CONTRACT: Requires injected ``OcelStoreProtocol``; optional ``short_names`` strips ``Action``/``Entity``/``Lifecycle`` suffixes from event and object type labels; read-only on event and pipeline state; E2O-only v1 (loaded one-hop FK, composite peer qualifiers).
    INVARIANTS: Zero frames → no ``add_event``; event attribute name conflicts → ``OcelContractError``; store must already be open in the owning action.
    AI-CORE-END
    """

    def __init__(
        self,
        store: OcelStoreProtocol,
        *,
        short_names: bool = False,
    ) -> None:
        super().__init__()
        self._store = store
        self._short_names = short_names

    async def get_initial_state(self) -> dict[str, Any]:
        return {}

    @on(GlobalFinishEvent, ignore_exceptions=False)
    async def on_export_ocel(
        self,
        state: dict[str, Any],
        event: GlobalFinishEvent,
        log: Any,
    ) -> dict[str, Any]:
        """Build ``OcelEvent`` from finish snapshots and append to the store."""
        frames = collect_ocel_frames(event)
        if not frames:
            return state
        ocel_event = self.build_ocel_event(frames, event)
        await self._store.add_event(ocel_event)
        return state

    def build_ocel_event(
        self,
        frames: Iterable[OcelFrame[BaseEntity]],
        event: GlobalFinishEvent,
    ) -> OcelEvent:
        """Assemble one composite ``OcelEvent`` from collected frames."""
        frame_list = list(frames)
        if not frame_list:
            raise OcelContractError("build_ocel_event requires at least one OcelFrame")

        relationships: list[OcelObjectRef] = []
        objects_by_id: dict[str, OcelObject] = {}
        for frame in frame_list:
            refs, objects = self._materialize_frame(frame)
            relationships.extend(refs)
            for obj in objects:
                objects_by_id[obj.id] = obj

        return OcelEvent(
            id=self._event_id(event),
            type=self._ocel_type_name(event.action_class),
            time=self._event_time(event),
            attributes=self._merge_event_attributes(frame_list),
            relationships=relationships,
            objects=list(objects_by_id.values()),
        )

    @staticmethod
    def ensure_utc(dt: datetime) -> datetime:
        """Normalize datetime to UTC for OCEL 2.0 JSON (naive → UTC)."""
        if dt.tzinfo is None:
            return dt.replace(tzinfo=UTC)
        return dt.astimezone(UTC)

    def _merge_event_attributes(
        self,
        frames: Iterable[OcelFrame[BaseEntity]],
    ) -> list[OcelAttribute]:
        merged: dict[str, OcelAttribute] = {}
        for frame in frames:
            for attr in frame.attributes:
                existing = merged.get(attr.name)
                if existing is not None and existing.value != attr.value:
                    raise OcelContractError(
                        f"Conflicting OcelEvent attribute {attr.name!r}: " f"{existing.value!r} vs {attr.value!r}"
                    )
                merged[attr.name] = attr
        return list(merged.values())

    def _materialize_frame(
        self,
        frame: OcelFrame[BaseEntity],
    ) -> tuple[list[OcelObjectRef], list[OcelObject]]:
        root = frame.object
        root_id = self._entity_object_id(root)
        objects = [self._build_ocel_object(root)]
        refs = [OcelObjectRef(object_id=root_id, qualifier=frame.qualifier)]

        for field_name, relation in root.get_foreign_keys().items():
            peer_qualifier = f"{frame.qualifier}.{field_name}"
            if isinstance(relation, BaseRelationOne):
                refs.extend(
                    self._materialize_relation_one(
                        root,
                        field_name,
                        relation,
                        peer_qualifier,
                        objects,
                    )
                )
            elif isinstance(relation, BaseRelationMany):
                refs.extend(
                    self._materialize_relation_many(
                        root,
                        field_name,
                        relation,
                        peer_qualifier,
                        objects,
                    )
                )
        return refs, objects

    def _materialize_relation_one(
        self,
        owner: BaseEntity,
        field_name: str,
        relation: BaseRelationOne[Any],
        peer_qualifier: str,
        objects: list[OcelObject],
    ) -> list[OcelObjectRef]:
        if relation.entity is not None:
            peer = relation.entity
            peer_id = self._entity_object_id(peer)
            if peer_id not in {obj.id for obj in objects}:
                objects.append(self._build_ocel_object(peer))
            return [OcelObjectRef(object_id=peer_id, qualifier=peer_qualifier)]

        related_cls = _related_entity_class(type(owner), field_name)
        if related_cls is None:
            raise OcelContractError(
                f"Cannot materialize id-only relation {field_name!r} on "
                f"{type(owner).__name__}: related entity type is unknown"
            )
        peer_id = make_oid(related_cls, relation.id)
        if peer_id not in {obj.id for obj in objects}:
            objects.append(
                OcelObject(
                    id=peer_id,
                    type=self._ocel_type_name(related_cls),
                    attributes=[OcelAttribute(name="id", value=str(relation.id))],
                )
            )
        return [OcelObjectRef(object_id=peer_id, qualifier=peer_qualifier)]

    def _materialize_relation_many(
        self,
        owner: BaseEntity,
        field_name: str,
        relation: BaseRelationMany[Any],
        peer_qualifier: str,
        objects: list[OcelObject],
    ) -> list[OcelObjectRef]:
        _ = owner
        _ = field_name
        if not relation.is_loaded:
            return []
        refs: list[OcelObjectRef] = []
        known_ids = {obj.id for obj in objects}
        for peer in relation.entities:
            peer_id = self._entity_object_id(peer)
            if peer_id not in known_ids:
                objects.append(self._build_ocel_object(peer))
                known_ids.add(peer_id)
            refs.append(OcelObjectRef(object_id=peer_id, qualifier=peer_qualifier))
        return refs

    def _build_ocel_object(self, entity: BaseEntity) -> OcelObject:
        attributes: list[OcelAttribute] = []
        for name, value in entity.get_scalar_fields().items():
            attributes.append(OcelAttribute(name=name, value=value))
        for name, lifecycle in entity.get_lifecycle_fields().items():
            attributes.append(OcelAttribute(name=name, value=lifecycle.current_state))
        return OcelObject(
            id=self._entity_object_id(entity),
            type=self._ocel_type_name(type(entity)),
            attributes=attributes,
        )

    def _ocel_type_name(self, cls: type) -> str:
        """Return OCEL event/object type label (FQN or short class name)."""
        return _ocel_type_name(cls, short_names=self._short_names)

    @staticmethod
    def _entity_object_id(entity: BaseEntity) -> str:
        pk = entity.get_primary_key()
        entity_id = pk.get("id")
        if entity_id is None:
            raise OcelContractError(f"Entity {type(entity).__name__} has no loaded primary key 'id' for OCEL export")
        return make_oid(entity, entity_id)

    @staticmethod
    def _event_id(event: GlobalFinishEvent) -> str:
        trace_id = event.context.request.trace_id
        if trace_id:
            return trace_id
        return str(uuid.uuid4())

    def _event_time(self, event: GlobalFinishEvent) -> datetime:
        ts = event.context.request.request_timestamp
        if ts is not None:
            return self.ensure_utc(ts)
        return datetime.now(UTC)


def collect_ocel_frames(
    source: GlobalFinishEvent | Mapping[str, Any] | None,
) -> list[OcelFrame[BaseEntity]]:
    """Collect ``OcelFrame`` rows from a finish event or one state-like mapping."""
    if source is None:
        return []
    if isinstance(source, GlobalFinishEvent):
        frames: list[OcelFrame[BaseEntity]] = []
        for snapshot in source.all_aspect_states:
            frames.extend(collect_ocel_frames(snapshot))
        frames.extend(collect_ocel_frames(_mapping_from_schema(source.result)))
        return frames

    payload = source
    if not payload:
        return []
    mapping_frames: list[OcelFrame[BaseEntity]] = []
    if OCEL_FRAMES_KEY in payload:
        mapping_frames.extend(_normalize_frame_values(payload[OCEL_FRAMES_KEY]))
    for value in payload.values():
        if isinstance(value, OcelFrame):
            mapping_frames.append(value)
    return mapping_frames


def _normalize_frame_values(value: Any) -> list[OcelFrame[BaseEntity]]:
    if isinstance(value, OcelFrame):
        return [value]
    if isinstance(value, (list, tuple)):
        return [item for item in value if isinstance(item, OcelFrame)]
    return []


def _mapping_from_schema(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump()
        if isinstance(dumped, Mapping):
            return dict(dumped)
    return {}


def _ocel_type_name(cls: type, *, short_names: bool) -> str:
    if not short_names:
        return f"{cls.__module__}.{cls.__qualname__}"
    name = cls.__name__
    for suffix in _OCEL_TYPE_SUFFIXES:
        if name.endswith(suffix) and len(name) > len(suffix):
            return name[: -len(suffix)]
    return name


def _unwrap_annotation(annotation: Any) -> Any:
    origin = get_origin(annotation)
    if origin is Annotated:
        return get_args(annotation)[0]
    if origin is Union:
        non_none = [arg for arg in get_args(annotation) if arg is not type(None)]
        if len(non_none) == 1:
            return _unwrap_annotation(non_none[0])
    return annotation


def _related_entity_class(
    owner: type[BaseEntity],
    field_name: str,
) -> type[BaseEntity] | None:
    field = owner.model_fields.get(field_name)
    if field is None:
        return None
    annotation = _unwrap_annotation(field.annotation)
    origin = get_origin(annotation)
    if origin is None:
        return None
    args = get_args(annotation)
    if not args:
        return None
    related = _unwrap_annotation(args[0])
    if isinstance(related, type) and issubclass(related, BaseEntity):
        return related
    return None
