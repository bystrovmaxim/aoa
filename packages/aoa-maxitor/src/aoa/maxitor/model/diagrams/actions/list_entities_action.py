# packages/aoa-maxitor/src/aoa/maxitor/model/diagrams/actions/list_entities_action.py
# mypy: ignore-errors
# pylint: disable=too-many-branches,too-many-statements
"""
ListEntitiesAction — one bounded-context ERD graph as JSON for the client.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Materialize ``{entities, relations}`` for a single ``domain_qualname`` so the SPA can
render ERD without server-generated HTML. Entity rows omit per-entity ``color``; the
browser injects accent hex from ``ListDomainsAction`` ``list_domains`` before rendering.
The ``list_entities`` field on ``Result`` uses the module-level ``ListEntitiesJson`` type from
``JsonSchemaValue.define`` (see :class:`~aoa.action_machine.model.json_schema_value.JsonSchemaValue`).

    Params.domain_qualname
          |
          v
    regular aspect  ->  ``erd_domain_class`` (:class:`~aoa.action_machine.domain.base_domain.BaseDomain` subclass)
          |
          v
    regular aspect  ->  ``erd_nx_coordinator`` + ``erd_graph_payload`` (coordinator + :class:`ErdGraphPayload`)
          |
          v
    summary aspect  ->  Result payload (labels + ``list_entities``)
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import Annotated, Any, Literal, cast, get_args, get_origin

from pydantic import Field

from aoa.action_machine.auth import NoneRole
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.domain.entity import BaseEntity
from aoa.action_machine.graph_model.nodes.entity_graph_node import EntityGraphNode
from aoa.action_machine.intents.aspects import regular_aspect, summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.checkers import result_instance
from aoa.action_machine.intents.connection import connection
from aoa.action_machine.intents.entity.entity_intent_resolver import EntityIntentResolver
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult, BaseState, JsonSchemaValue
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.runtime.tools_box import ToolsBox
from aoa.action_machine.system_core.type_introspection import TypeIntrospection
from aoa.graph.node_graph_coordinator import NodeGraphCoordinator
from aoa.maxitor.model.core.resources.service_graph_resource import (
    SERVICE_GRAPH_CONNECTION_KEY,
    ServiceGraphResource,
)
from aoa.maxitor.model.diagrams.interchange_nx_coordinator import node_graph_coordinator_from_interchange_nx
from aoa.maxitor.model.diagrams.diagrams_domain import DiagramsDomain


def _entity_nodes_by_id(coordinator: NodeGraphCoordinator) -> dict[str, EntityGraphNode]:
    return {node.node_id: node for node in coordinator.get_all_nodes() if isinstance(node, EntityGraphNode)}


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


def _append_relationship_edge_from_row(
    *,
    relationships: list[ErdEdgeSpec],
    field_map: dict[str, dict[str, ErdFieldSpec]],
    by_id: dict[str, EntityGraphNode],
    row: tuple[str, str, str, dict[str, Any]],
) -> None:
    """Emit one directed relationship row into ``relationships`` and merge FK compartments."""
    c_src, c_tgt, c_field, c_props = row
    cardinality = c_props.get("cardinality", "")
    label_field = c_field or str(c_props.get("field_name", "") or "")
    chosen_is_to_one_fk = str(cardinality or "") == "one"
    src_card, tgt_card = _cardinality_pair_for_chosen_relation(
        str(cardinality or ""),
        chosen_is_to_one_fk=chosen_is_to_one_fk,
    )
    if label_field:
        label = label_field if not cardinality else f"{label_field} ({cardinality})"
        rid_field = label_field
        existing = field_map.setdefault(c_src, {}).get(label_field)
        fk_type = f"FK -> {by_id[c_tgt].node_obj.__name__}" if c_tgt in by_id else "FK"
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
        label = str(cardinality or "")
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


def erd_payload_from_coordinator_for_domain(
    coordinator: NodeGraphCoordinator,
    domain_cls: type[BaseDomain],
) -> ErdGraphPayload:
    """
    Read the coordinator graph for one bounded context and assemble transient ERD rows.

    AI-CORE-BEGIN
    ROLE: Read interchange ``Entity`` vertices and ``entity_relation`` associations into transient ERD rows.
    CONTRACT: Rows are anchored at ``domain_cls``; association edges whose far end lives in another declared domain appear as FK slots and stubs for that foreign entity (same Annotated semantics as intra-domain graphs).
    INVERSE pairs with **matching** cardinality (``AssociationOne`` / ``one``+``one``) still collapse or dual-emit using inverse slot bookkeeping.
    INVARIANTS: Every diagram vertex maps to an ``EntityGraphNode`` id on the built coordinator graph.
    AI-CORE-END
    """
    domain_qual = TypeIntrospection.full_qualname(domain_cls)
    all_graph = _entity_nodes_by_id(coordinator)

    by_dom: dict[str, EntityGraphNode] = {}
    for node in coordinator.get_all_nodes():
        if not isinstance(node, EntityGraphNode):
            continue
        if node.domain.target_node_id != domain_qual:
            continue
        by_dom[node.node_id] = node

    entity_ids_dom = frozenset(by_dom)

    relation_rows: list[tuple[str, str, str, dict[str, Any]]] = []
    for src_id in sorted(entity_ids_dom):
        ent_node = by_dom[src_id]
        for assoc in ent_node.relations:
            tgt = assoc.target_node_id
            if tgt not in all_graph:
                continue
            props = assoc.properties
            field_name = str(props.get("field_name", "") or "")
            relation_rows.append((src_id, tgt, field_name, props))

    for src_id in sorted(all_graph.keys()):
        if src_id in entity_ids_dom:
            continue
        ext_node = all_graph[src_id]
        for assoc in ext_node.relations:
            tgt = assoc.target_node_id
            if tgt not in entity_ids_dom:
                continue
            props = assoc.properties
            field_name = str(props.get("field_name", "") or "")
            relation_rows.append((src_id, tgt, field_name, props))

    display_ids: set[str] = set(entity_ids_dom)
    for src, tgt, _, _ in relation_rows:
        if src in all_graph:
            display_ids.add(src)
        if tgt in all_graph:
            display_ids.add(tgt)

    field_map: dict[str, dict[str, ErdFieldSpec]] = {}
    for eid in sorted(display_ids):
        node_row = all_graph[eid]
        fields = entity_fields_from_class(node_row.node_obj)
        field_map[eid] = {f.name: f for f in fields}

    relationships: list[ErdEdgeSpec] = []
    emitted_inverse_pairs: set[frozenset[tuple[str, str]]] = set()
    by_slot = {
        (src, field_name): (src, tgt, field_name, props) for src, tgt, field_name, props in relation_rows if field_name
    }
    for src_id, tgt, field_name, props in relation_rows:
        inv_entity_id = props.get("inverse_entity_id")
        inv_field = props.get("inverse_field")
        inverse_slot = (
            (str(inv_entity_id), str(inv_field))
            if inv_entity_id is not None and inv_field is not None and str(inv_field).strip()
            else None
        )
        inverse_key = frozenset(((src_id, field_name), inverse_slot)) if inverse_slot is not None else None
        if inverse_key is not None and inverse_key in emitted_inverse_pairs:
            continue

        chosen = (src_id, tgt, field_name, props)
        row_self = (src_id, tgt, field_name, props)
        if inverse_key is not None and inverse_slot is not None and (inv := by_slot.get(inverse_slot)) is not None:
            this_card = str(props.get("cardinality", "") or "")
            inv_card = str(inv[3].get("cardinality", "") or "")
            emitted_inverse_pairs.add(inverse_key)
            if this_card == "many" and inv_card == "one":
                _append_relationship_edge_from_row(
                    relationships=relationships,
                    field_map=field_map,
                    by_id=all_graph,
                    row=inv,
                )
            elif this_card == inv_card:
                _append_relationship_edge_from_row(
                    relationships=relationships,
                    field_map=field_map,
                    by_id=all_graph,
                    row=row_self,
                )
                _append_relationship_edge_from_row(
                    relationships=relationships,
                    field_map=field_map,
                    by_id=all_graph,
                    row=inv,
                )
            else:
                cand = min(row_self, inv, key=lambda row: (row[0], row[2]))
                _append_relationship_edge_from_row(
                    relationships=relationships,
                    field_map=field_map,
                    by_id=all_graph,
                    row=cand,
                )
            continue

        _append_relationship_edge_from_row(
            relationships=relationships,
            field_map=field_map,
            by_id=all_graph,
            row=chosen,
        )

    entities = tuple(
        ErdEntitySpec(
            id=eid,
            label=all_graph[eid].node_obj.__name__,
            attributes=entity_attributes_from_class(all_graph[eid].node_obj),
            fields=tuple(field_map[eid].values()),
            is_junction=sum(1 for f in field_map[eid].values() if "fk" in f.role) >= 2
            and sum(1 for f in field_map[eid].values() if f.role == "field") <= 3,
        )
        for eid in sorted(display_ids)
    )
    return ErdGraphPayload(entities=entities, relationships=tuple(relationships))


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

# One bounded-context ERD slice for ``ListEntitiesAction.Result.list_entities``: ``entities`` carry
# interchange entity ids, display labels, and tabular field rows; ``relations`` connect entity ids
# with a display label, ``relationship_kind``, and source/target cardinalities (``ERD_DATA`` domain payload).
ListEntitiesJson = JsonSchemaValue.define(
    name="ListEntitiesJson",
    schema={
        "type": "object",
        "properties": {
            "entities": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "label": {"type": "string"},
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
                    "required": ["id", "label", "fields"],
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
    },
)


@meta(
    description="List entities, fields, and relations for one interchange domain qualname (diagrams)",
    domain=DiagramsDomain,
)
@check_roles(NoneRole)
@connection(ServiceGraphResource, key=SERVICE_GRAPH_CONNECTION_KEY, description="Interchange nx graph from LoadGraphAction")
class ListEntitiesAction(
    BaseAction["ListEntitiesAction.Params", "ListEntitiesAction.Result"],
):
    """
    AI-CORE-BEGIN
    ROLE: Emit one domain slice of ``ERD_DATA``-shaped JSON (``list_entities``) for client rendering.
    CONTRACT: ``domain_qualname`` is the full interchange node id for a ``BaseDomain`` class.
    INVARIANTS: Reads the graph only via ``connections["ServiceGraph"].service``; regular aspects
    populate ``erd_domain_class``, then ``erd_nx_coordinator`` / ``erd_graph_payload`` together, before summary serialization.
    AI-CORE-END
    """

    class Params(BaseParams):
        domain_qualname: str = Field(min_length=1, description="Full qualname of the BaseDomain interchange node id")

    class Result(BaseResult):
        domain_label: str = Field(min_length=1, description="Human tab label (domain name or class name)")
        domain_qualname: str = Field(min_length=1, description="Same interchange qualname as in Params (echoed on the wire).")
        # {
        #   "entities": [
        #     {
        #       "id": "aoa.orders.entity.OrderEntity",
        #       "label": "Order",
        #       "fields": [
        #         {"name": "id", "type": "str", "primary_key": true, "foreign_key": false}
        #       ]
        #     }
        #   ],
        #   "relations": [
        #     {
        #       "source": "aoa.orders.entity.OrderEntity",
        #       "target": "aoa.orders.entity.LineItemEntity",
        #       "label": "line_items",
        #       "relationship_kind": "association",
        #       "source_cardinality": "one",
        #       "target_cardinality": "zero_many"
        #     }
        #   ]
        # }
        list_entities: ListEntitiesJson = Field(
            description=(
                "ERD slice for this domain: ``entities`` are interchange entity ids with display labels "
                "and tabular ``fields`` (name, type string, PK/FK flags); ``relations`` connect entity ids "
                "with a display ``label``, ``relationship_kind``, and ``source_cardinality`` / "
                "``target_cardinality``. Shape matches ``ERD_DATA`` domain payloads."
            ),
        )

    @regular_aspect("Resolve interchange BaseDomain class from qualname")
    @result_instance("erd_domain_class", type, required=True)  # type: ignore[untyped-decorator]
    async def resolve_erd_domain_class_aspect(
        self,
        params: ListEntitiesAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> dict[str, Any]:
        qual = params.domain_qualname.strip()
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
                domain_cls: type[BaseDomain] = obj
                return {"erd_domain_class": domain_cls}
        msg = f"Not a BaseDomain subclass or not importable: {qual!r}"
        raise TypeError(msg)

    @regular_aspect("Recover coordinator from nx graph and assemble transient ERD rows for the domain")
    @result_instance("erd_domain_class", type, required=True)  # type: ignore[untyped-decorator]
    @result_instance("erd_nx_coordinator", NodeGraphCoordinator, required=True)  # type: ignore[untyped-decorator]
    @result_instance("erd_graph_payload", ErdGraphPayload, required=True)  # type: ignore[untyped-decorator]
    async def materialize_coordinator_and_erd_payload_aspect(
        self,
        params: ListEntitiesAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> dict[str, Any]:
        nx_resource = cast(ServiceGraphResource, connections[SERVICE_GRAPH_CONNECTION_KEY])
        coordinator = node_graph_coordinator_from_interchange_nx(nx_resource.service)
        dc = cast(type[BaseDomain], state["erd_domain_class"])
        payload = erd_payload_from_coordinator_for_domain(coordinator, dc)
        # BaseState is replaced entirely per aspect; carry forward keys prior aspects produced.
        return {**state.to_dict(), "erd_nx_coordinator": coordinator, "erd_graph_payload": payload}

    @summary_aspect("Serialize ERD slice and domain labels for HTTP JSON")
    async def build_domain_payload_summary(
        self,
        params: ListEntitiesAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> ListEntitiesAction.Result:
        qual = params.domain_qualname.strip()
        dc = cast(type[BaseDomain], state["erd_domain_class"])
        payload = cast(ErdGraphPayload, state["erd_graph_payload"])
        base = getattr(dc, "name", None) or dc.__name__
        return ListEntitiesAction.Result(
            domain_label=str(base),
            domain_qualname=qual,
            list_entities=payload_to_domain_dict(payload),
        )
