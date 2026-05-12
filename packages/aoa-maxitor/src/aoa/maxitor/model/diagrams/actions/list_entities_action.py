# packages/aoa-maxitor/src/aoa/maxitor/model/diagrams/actions/list_entities_action.py
# mypy: ignore-errors
# pylint: disable=too-many-branches,too-many-statements
"""
ListEntitiesAction — ERD entity/field/relation JSON for one or more interchange domains.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Materialize ``{entities, relations}`` slices for each requested ``BaseDomain`` interchange id so
the SPA can render ERD without server-generated HTML. A single action call scans the serialized
NetworkX graph once and emits ``domain_slices`` (possibly empty when no domains are requested).
Entity rows omit per-entity ``color``; the browser injects accent hex from ``ListDomainsAction``.

    Params: ``domain_qualnames`` as ``list[str]`` (HTTP: repeat ``domain_qualnames`` per item, OpenAPI ``explode``) + ``include_one_hop_neighbors``
          |
          v
    summary aspect  ->  ``Result(domain_slices=[...])``
"""

from __future__ import annotations

import copy
import importlib
from dataclasses import dataclass, field
from typing import Annotated, Any, Literal, cast, get_args, get_origin

from pydantic import Field

from aoa.action_machine.auth import NoneRole
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.domain.entity import BaseEntity
from aoa.action_machine.integrations.fastapi.query_field_before import QUERY_STR_LIST_BEFORE
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.connection import connection
from aoa.action_machine.intents.entity.entity_intent_resolver import EntityIntentResolver
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult, BaseState, JsonSchemaValue
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.runtime.tools_box import ToolsBox
from aoa.maxitor.model.core.resources.networkx_graph_resource import (
    NETWORKX_GRAPH_CONNECTION_KEY,
    NetworkXGraphResource,
)
from aoa.maxitor.model.diagrams.diagrams_domain import DiagramsDomain

FieldRole = Literal["pk", "fk", "pk_fk", "field"]
Cardinality = Literal["one", "zero_one", "one_many", "zero_many"]


@dataclass(frozen=True)
class ErdFieldSpec:
    """
    One visible ERD table row.

    AI-CORE-BEGIN
    ROLE: Preserve relational-table semantics for one field row before cell-graph serialization.
    CONTRACT: ``role`` controls the PK/FK compartment; ``references`` stores the referenced table id when this is an FK row.
    AI-CORE-END
    """

    name: str
    type: str = ""
    role: FieldRole = "field"
    references: str = ""
    nullable: bool = False


@dataclass(frozen=True)
class ErdEntitySpec:
    """One ERD entity (human label + field rows)."""

    id: str
    label: str
    #: Interchange qualname of the ``BaseDomain`` this entity belongs to (``domain`` edge target).
    domain_qualname: str = ""
    attributes: dict[str, Any] = field(default_factory=dict)
    fields: tuple[ErdFieldSpec, ...] = ()
    is_junction: bool = False


@dataclass(frozen=True)
class ErdEdgeSpec:
    """Logical ERD relationship between two entity node ids."""

    id: str
    source: str
    target: str
    label: str = ""
    #: Relation field name on ``source`` (used for FK row + edge label text).
    source_field: str = ""
    target_field: str = "id"
    source_cardinality: Cardinality = "zero_many"
    target_cardinality: Cardinality = "one"
    relationship_kind: str = "association"


@dataclass
class ErdGraphPayload:
    """Transient ERD rows assembled while reading the coordinator graph."""

    entities: tuple[ErdEntitySpec, ...]
    relationships: tuple[ErdEdgeSpec, ...]


@dataclass(frozen=True)
class ErdSeedPayload:
    """Domain-local ERD rows and boundary relations discovered from the selected domain."""

    all_entities: dict[str, dict[str, Any]]
    domain_entity_ids: frozenset[str]
    relation_rows: tuple[tuple[str, str, str, dict[str, Any]], ...]
    #: Every entity id with a ``domain`` edge in the graph → that domain's interchange qualname.
    entity_domain_qualname: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ErdNxScan:
    """Single pass over the serialized NetworkX graph for ERD materialization."""

    all_entities: dict[str, dict[str, Any]]
    relation_rows: tuple[tuple[str, str, str, dict[str, Any]], ...]
    #: Canonical interchange qualname per entity (smallest ``dqual`` when multiple domain edges exist).
    entity_domain_qualname: dict[str, str]
    #: Entity ids that have a ``domain`` edge to each interchange domain qualname (matches prior per-domain seeding).
    domain_entity_ids_by_domain: dict[str, frozenset[str]]


def _relation_slot_names(entity_cls: type[BaseEntity]) -> frozenset[str]:
    return frozenset(rel.field_name for rel in EntityIntentResolver.resolve_entity_relations(entity_cls))


def _pretty_annotation(annotation: Any) -> str:
    """Best-effort type string for ERD ports (drops ``Annotated`` metadata)."""
    ann = annotation
    while get_origin(ann) is Annotated:
        args_a = get_args(ann)
        if not args_a:
            break
        ann = args_a[0]
    origin = get_origin(ann)
    args_inner = get_args(ann)
    if origin is None:
        return ann.__qualname__ if isinstance(ann, type) else str(ann)
    bits = [_pretty_annotation(a) for a in args_inner]
    oname = getattr(origin, "__qualname__", str(origin))
    return f"{oname}[{', '.join(bits)}]" if bits else oname


def entity_attributes_from_class(entity_cls: type[BaseEntity]) -> dict[str, str]:
    """Non-relation model fields → column type strings."""
    skip = _relation_slot_names(entity_cls)
    return {
        name: _pretty_annotation(finfo.annotation)
        for name, finfo in entity_cls.model_fields.items()
        if name not in skip
    }


def entity_fields_from_class(entity_cls: type[BaseEntity]) -> tuple[ErdFieldSpec, ...]:
    """Non-relation model fields as ERD rows (declaration order); ``id`` is the PK row."""
    attrs = entity_attributes_from_class(entity_cls)
    out: list[ErdFieldSpec] = []
    if "id" not in attrs:
        out.append(ErdFieldSpec(name="id", type="str", role="pk"))
    for name, typ in attrs.items():
        role: FieldRole = "pk" if name == "id" else "field"
        out.append(ErdFieldSpec(name=name, type=str(typ), role=role))
    return tuple(out)


def _cardinality_pair_for_chosen_relation(
    src_cardinality: str,
    *,
    chosen_is_to_one_fk: bool,
) -> tuple[Cardinality, Cardinality]:
    """
    Return cardinalities for ``(source, target)`` after choosing the displayed edge direction.

    A to-one FK row means many source rows may reference one target row; a to-many collection
    means one source row owns/associates many target rows.
    """
    if chosen_is_to_one_fk or src_cardinality == "one":
        return "zero_many", "one"
    return "one", "zero_many"


def _merge_field_role(existing: FieldRole, incoming: FieldRole) -> FieldRole:
    if existing == incoming:
        return existing
    if "pk" in {existing, incoming} and "fk" in {existing, incoming}:
        return "pk_fk"
    if existing == "pk_fk" or incoming == "pk_fk":
        return "pk_fk"
    return incoming if incoming != "field" else existing


def _node_type(row: dict[str, Any]) -> str:
    return str(row.get("type", row.get("node_type", "")) or "")


def _edge_type(row: dict[str, Any]) -> str:
    return str(row.get("type", row.get("edge_name", "")) or "")


def _class_from_qualname(qualname: str) -> type[Any] | None:
    parts = qualname.split(".")
    for mod_len in range(len(parts) - 1, 0, -1):
        mod_name = ".".join(parts[:mod_len])
        attr_path = parts[mod_len:]
        try:
            module = importlib.import_module(mod_name)
        except ModuleNotFoundError:
            continue
        obj: Any = module
        try:
            for attr in attr_path:
                obj = getattr(obj, attr)
        except AttributeError:
            continue
        if isinstance(obj, type):
            return obj
    return None


def _entity_fields_from_json_node(entity_id: str) -> tuple[ErdFieldSpec, ...]:
    entity_cls = _class_from_qualname(entity_id)
    if isinstance(entity_cls, type) and issubclass(entity_cls, BaseEntity):
        return entity_fields_from_class(entity_cls)
    return (ErdFieldSpec(name="id", type="str", role="pk"),)


def _entity_attributes_from_json_node(entity_id: str) -> dict[str, str]:
    entity_cls = _class_from_qualname(entity_id)
    if isinstance(entity_cls, type) and issubclass(entity_cls, BaseEntity):
        return entity_attributes_from_class(entity_cls)
    return {}


def erd_scan_networkx(nx_graph: Any) -> ErdNxScan:
    """One graph walk: entities, relation rows, canonical domain labels, per-domain membership."""
    all_entities: dict[str, dict[str, Any]] = {
        str(nid): dict(data)
        for nid, data in nx_graph.nodes(data=True)
        if _node_type(dict(data)) == "Entity"
    }

    entity_domain_qualname: dict[str, str] = {}
    domain_entity_ids_by_domain: dict[str, set[str]] = {}
    relation_rows: list[tuple[str, str, str, dict[str, Any]]] = []

    for source, target, data in nx_graph.edges(data=True):
        src = str(source)
        tgt = str(target)
        edge = dict(data)
        etype = _edge_type(edge)
        props = dict(edge.get("properties") or {})
        if etype == "domain" and src in all_entities:
            dqual = str(tgt)
            domain_entity_ids_by_domain.setdefault(dqual, set()).add(src)
            prev = entity_domain_qualname.get(src)
            if prev is None or dqual < prev:
                entity_domain_qualname[src] = dqual
        elif etype == "entity_relation":
            field_name = str(props.get("field_name", "") or "")
            relation_rows.append((src, tgt, field_name, props))

    return ErdNxScan(
        all_entities=all_entities,
        relation_rows=tuple(relation_rows),
        entity_domain_qualname=entity_domain_qualname,
        domain_entity_ids_by_domain={k: frozenset(v) for k, v in domain_entity_ids_by_domain.items()},
    )


def erd_seed_from_scan(scan: ErdNxScan, domain_qual: str) -> ErdSeedPayload:
    """Domain-local seed using a shared :class:`ErdNxScan` (same semantics as the former single-graph walk)."""
    return ErdSeedPayload(
        all_entities=scan.all_entities,
        domain_entity_ids=scan.domain_entity_ids_by_domain.get(domain_qual, frozenset()),
        relation_rows=scan.relation_rows,
        entity_domain_qualname=dict(scan.entity_domain_qualname),
    )


def _one_hop_entity_ids(seed: ErdSeedPayload) -> frozenset[str]:
    """Entity ids reached by seed relations, excluding entities already in the selected domain."""
    out: set[str] = set()
    for src, tgt, _, _ in seed.relation_rows:
        if src in seed.domain_entity_ids and tgt in seed.all_entities and tgt not in seed.domain_entity_ids:
            out.add(tgt)
        if tgt in seed.domain_entity_ids and src in seed.all_entities and src not in seed.domain_entity_ids:
            out.add(src)
    return frozenset(out)


def erd_payload_from_seed(
    seed: ErdSeedPayload,
    one_hop_entity_ids: frozenset[str],
) -> ErdGraphPayload:
    """Build final ERD payload from domain entities plus optional one-hop entities."""
    all_entities = seed.all_entities
    selected_entity_ids = frozenset((*seed.domain_entity_ids, *one_hop_entity_ids))
    intra_domain_rows = [
        row
        for row in seed.relation_rows
        if row[0] in seed.domain_entity_ids and row[1] in seed.domain_entity_ids
    ]
    # One-hop neighbors are discovered from the full graph, but we still omit second-hop:
    # only edges that tie a domain entity to an included one-hop entity (not one_hop–one_hop).
    boundary_rows = (
        [
            row
            for row in seed.relation_rows
            if (row[0] in seed.domain_entity_ids and row[1] in one_hop_entity_ids)
            or (row[1] in seed.domain_entity_ids and row[0] in one_hop_entity_ids)
        ]
        if one_hop_entity_ids
        else []
    )
    relation_rows = [*intra_domain_rows, *boundary_rows]

    display_ids: set[str] = set(selected_entity_ids)
    for src, tgt, _, _ in relation_rows:
        if src in all_entities:
            display_ids.add(src)
        if tgt in all_entities:
            display_ids.add(tgt)

    field_map: dict[str, dict[str, ErdFieldSpec]] = {
        eid: {field.name: field for field in _entity_fields_from_json_node(eid)}
        for eid in sorted(display_ids)
    }

    relationships: list[ErdEdgeSpec] = []
    for row in relation_rows:
        _append_relationship_edge_from_row_json(
            relationships=relationships,
            field_map=field_map,
            entity_rows=all_entities,
            row=row,
        )

    entities = tuple(
        ErdEntitySpec(
            id=eid,
            label=str(all_entities[eid].get("label", eid.rsplit(".", 1)[-1])),
            domain_qualname=str(seed.entity_domain_qualname.get(eid, "") or ""),
            attributes=_entity_attributes_from_json_node(eid),
            fields=tuple(field_map[eid].values()),
            is_junction=sum(1 for f in field_map[eid].values() if "fk" in f.role) >= 2
            and sum(1 for f in field_map[eid].values() if f.role == "field") <= 3,
        )
        for eid in sorted(display_ids)
    )
    return ErdGraphPayload(entities=entities, relationships=tuple(relationships))


def _append_relationship_edge_from_row_json(
    *,
    relationships: list[ErdEdgeSpec],
    field_map: dict[str, dict[str, ErdFieldSpec]],
    entity_rows: dict[str, dict[str, Any]],
    row: tuple[str, str, str, dict[str, Any]],
) -> None:
    """Emit one ERD relationship from JSON-exported edge properties."""
    c_src, c_tgt, c_field, c_props = row
    cardinality = str(c_props.get("cardinality", "") or "")
    label_field = c_field or str(c_props.get("field_name", "") or "")
    chosen_is_to_one_fk = cardinality == "one"
    src_card, tgt_card = _cardinality_pair_for_chosen_relation(
        cardinality,
        chosen_is_to_one_fk=chosen_is_to_one_fk,
    )
    if label_field:
        label = label_field if not cardinality else f"{label_field} ({cardinality})"
        rid_field = label_field
        existing = field_map.setdefault(c_src, {}).get(label_field)
        target_label = str(entity_rows.get(c_tgt, {}).get("label", "") or c_tgt.rsplit(".", 1)[-1])
        fk_type = f"FK -> {target_label}" if c_tgt in entity_rows else "FK"
        if existing is None:
            field_map[c_src][label_field] = ErdFieldSpec(
                name=label_field,
                type=fk_type,
                role="fk",
                references=c_tgt,
            )
        else:
            field_map[c_src][label_field] = ErdFieldSpec(
                name=existing.name,
                type=existing.type if existing.type else fk_type,
                role=_merge_field_role(existing.role, "fk"),
                references=existing.references or c_tgt,
                nullable=existing.nullable,
            )
    else:
        label = cardinality
        rid_field = "relation"
    rid = f"rel.{c_src}.{rid_field}".replace(":", "_")
    relationships.append(
        ErdEdgeSpec(
            id=rid,
            source=c_src,
            target=c_tgt,
            label=label,
            source_field=label_field,
            source_cardinality=src_card,
            target_cardinality=tgt_card,
            relationship_kind=str(c_props.get("relation_type", "") or "association"),
        ),
    )


def _role_to_flags(role: str) -> dict[str, bool]:
    """Convert a field role string into boolean flags for JS."""
    return {
        "primary_key": role in ("pk", "pk_fk"),
        "foreign_key": role in ("fk", "pk_fk"),
    }


def _serialize_entity(entity: ErdEntitySpec) -> dict[str, Any]:
    """Convert ErdEntitySpec into the JS entity-row shape (shared with the React ERD viewer ``ERD_DATA`` JSON)."""
    fields: list[dict[str, Any]] = []
    for f in entity.fields:
        flags = _role_to_flags(f.role)
        fields.append(
            {
                "name": f.name,
                "type": f.type or "",
                "primary_key": flags["primary_key"],
                "foreign_key": flags["foreign_key"],
            }
        )
    if not fields:
        fields.append({"name": "id", "type": "str", "primary_key": True, "foreign_key": False})
        for k, v in (entity.attributes or {}).items():
            if k == "id":
                continue
            fields.append({"name": k, "type": str(v), "primary_key": False, "foreign_key": False})
    return {
        "id": entity.id,
        "label": entity.label,
        "domain_qualname": entity.domain_qualname,
        "fields": fields,
    }


def _serialize_edge(rel: ErdEdgeSpec) -> dict[str, Any]:
    """Convert ErdEdgeSpec into the JS relation shape."""
    return {
        "source": rel.source,
        "target": rel.target,
        "label": rel.label or "",
        "relationship_kind": rel.relationship_kind,
        "source_cardinality": rel.source_cardinality,
        "target_cardinality": rel.target_cardinality,
    }


def payload_to_domain_dict(payload: ErdGraphPayload) -> dict[str, Any]:
    """Convert ErdGraphPayload into the JSON-ready domain dictionary for ``ERD_DATA``."""
    serialized_entities: list[dict[str, Any]] = []
    for entity in payload.entities:
        serialized_entities.append(_serialize_entity(entity))

    relations = [_serialize_edge(rel) for rel in payload.relationships]
    return {"entities": serialized_entities, "relations": relations}


_ERD_RELATION_CARDINALITY = {"type": "string", "enum": ["one", "zero_one", "one_many", "zero_many"]}

# ``{entities, relations}`` for one bounded context — same shape as ``ERD_DATA`` domain payloads.
_LIST_ENTITIES_ERD_PAYLOAD_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "entities": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "label": {"type": "string"},
                    "domain_qualname": {
                        "type": "string",
                        "description": "Interchange qualname of the BaseDomain owning this entity (for accent coloring).",
                    },
                    "fields": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "type": {"type": "string"},
                                "primary_key": {"type": "boolean"},
                                "foreign_key": {"type": "boolean"},
                            },
                            "required": [
                                "name",
                                "type",
                                "primary_key",
                                "foreign_key",
                            ],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": ["id", "label", "domain_qualname", "fields"],
                "additionalProperties": False,
            },
        },
        "relations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "source": {"type": "string"},
                    "target": {"type": "string"},
                    "label": {"type": "string"},
                    "relationship_kind": {"type": "string"},
                    "source_cardinality": _ERD_RELATION_CARDINALITY,
                    "target_cardinality": _ERD_RELATION_CARDINALITY,
                },
                "required": [
                    "source",
                    "target",
                    "label",
                    "relationship_kind",
                    "source_cardinality",
                    "target_cardinality",
                ],
                "additionalProperties": False,
            },
        },
    },
    "required": ["entities", "relations"],
    "additionalProperties": False,
}

ListEntitiesJson = JsonSchemaValue.define(
    name="ListEntitiesJson",
    schema=_LIST_ENTITIES_ERD_PAYLOAD_SCHEMA,
)

_LIST_ENTITIES_DOMAIN_SLICE_OBJECT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "domain_label": {"type": "string", "minLength": 1},
        "domain_qualname": {"type": "string", "minLength": 1},
        "list_entities": copy.deepcopy(_LIST_ENTITIES_ERD_PAYLOAD_SCHEMA),
    },
    "required": ["domain_label", "domain_qualname", "list_entities"],
    "additionalProperties": False,
}

ListEntitiesDomainSlicesJson = JsonSchemaValue.define(
    name="ListEntitiesDomainSlicesJson",
    schema={
        "type": "array",
        "items": copy.deepcopy(_LIST_ENTITIES_DOMAIN_SLICE_OBJECT_SCHEMA),
    },
)


def _domain_qualnames_from_param(raw: str) -> list[str]:
    """Split the single ``domain_qualnames`` query field into tokens (comma-separated, trimmed, empties dropped)."""
    if not (raw or "").strip():
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]


def _resolve_base_domain_class(qual: str) -> type[BaseDomain]:
    """Import path resolution for ``BaseDomain`` interchange ids (same rules as the former aspect)."""
    if "." not in qual:
        msg = f"Invalid domain type qualname: {qual!r}"
        raise ValueError(msg)
    parts = qual.split(".")
    for mod_len in range(len(parts) - 1, 0, -1):
        mod_name = ".".join(parts[:mod_len])
        attr_path = parts[mod_len:]
        try:
            module = importlib.import_module(mod_name)
        except ModuleNotFoundError:
            continue
        obj: Any = module
        try:
            for attr in attr_path:
                obj = getattr(obj, attr)
        except AttributeError:
            continue
        if isinstance(obj, type) and issubclass(obj, BaseDomain):
            return obj
    msg = f"Not a BaseDomain subclass or not importable: {qual!r}"
    raise TypeError(msg)


@meta(
    description="List entities, fields, and relations for interchange domain qualnames (diagrams)",
    domain=DiagramsDomain,
)
@check_roles(NoneRole)
@connection(NetworkXGraphResource, key=NETWORKX_GRAPH_CONNECTION_KEY, description="Serialized interchange nx graph")
class ListEntitiesAction(
    BaseAction["ListEntitiesAction.Params", "ListEntitiesAction.Result"],
):
    """
    AI-CORE-BEGIN
    ROLE: Emit ``ERD_DATA``-shaped JSON slices for each requested ``BaseDomain`` interchange id.
    CONTRACT: ``domain_qualnames`` is ``list[str]``; over HTTP repeat the ``domain_qualnames`` query key
              once per interchange id (OpenAPI ``array`` + ``explode``). Order is preserved; duplicates and
              blank tokens are ignored. The graph is scanned once per action call.
    INVARIANTS: Reads the graph only via ``connections["NetworkXGraph"].service``.
    AI-CORE-END
    """

    class Params(BaseParams):
        domain_qualnames: Annotated[list[str], QUERY_STR_LIST_BEFORE] = Field(
            default_factory=list,
            description=(
                "BaseDomain interchange node ids. HTTP: repeat the ``domain_qualnames`` query parameter "
                "once per id (``?domain_qualnames=a&domain_qualnames=b``). Omit entirely for no domains."
            ),
        )
        include_one_hop_neighbors: bool = Field(
            default=True,
            description=(
                "Include BaseEntity interchange nodes one ``entity_relation`` edge away from a domain entity "
                "(often in another bounded context). When true, draw those boundary edges; omit second-hop pairs "
                "and omit one-hop–one-hop edges."
            ),
        )

    class Result(BaseResult):
        domain_slices: ListEntitiesDomainSlicesJson = Field(
            description=(
                "One entry per requested domain (after de-duplication): ``domain_label``, echoed ``domain_qualname``, "
                "and ``list_entities`` with ``entities`` / ``relations`` matching ``ERD_DATA`` domain payloads."
            ),
        )

    @summary_aspect("Serialize ERD slices for requested domains (single graph scan)")
    async def build_domain_payload_summary(
        self,
        params: ListEntitiesAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> ListEntitiesAction.Result:
        nx_resource = cast(NetworkXGraphResource, connections[NETWORKX_GRAPH_CONNECTION_KEY])
        scan = erd_scan_networkx(nx_resource.service)

        seen: set[str] = set()
        ordered_quals: list[str] = []
        for raw in params.domain_qualnames:
            q = raw.strip()
            if not q or q in seen:
                continue
            seen.add(q)
            ordered_quals.append(q)

        if not ordered_quals:
            return ListEntitiesAction.Result(domain_slices=[])

        slices: list[dict[str, Any]] = []
        for qual in ordered_quals:
            dc = _resolve_base_domain_class(qual)
            seed = erd_seed_from_scan(scan, qual)
            one_hop_ids = _one_hop_entity_ids(seed) if params.include_one_hop_neighbors else frozenset()
            payload = erd_payload_from_seed(seed, one_hop_ids)
            base = getattr(dc, "name", None) or dc.__name__
            slices.append(
                {
                    "domain_label": str(base),
                    "domain_qualname": qual,
                    "list_entities": payload_to_domain_dict(payload),
                },
            )

        return ListEntitiesAction.Result(domain_slices=slices)
