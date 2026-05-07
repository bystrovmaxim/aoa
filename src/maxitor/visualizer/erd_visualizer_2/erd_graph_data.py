# src/maxitor/visualizer/erd_visualizer_2/erd_graph_data.py
# mypy: ignore-errors
# pylint: disable=too-many-branches,too-many-statements
"""
Pure data layer for normalized ERD-style graphs — no browser runtime.

Produces an AntV **X6** graph document (``{ "cells": [...] }``) for :mod:`erd_html`
by reading the current :class:`~graph.node_graph_coordinator.NodeGraphCoordinator`
graph at export time. Sample entities stay one class per file; ERD rows come from
their live graph metadata and declared relation fields.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Annotated, Any, Literal, get_args, get_origin

from action_machine.domain.base_domain import BaseDomain
from action_machine.domain.entity import BaseEntity
from action_machine.graph_model.nodes.entity_graph_node import EntityGraphNode
from action_machine.intents.entity.entity_intent_resolver import EntityIntentResolver
from action_machine.system_core.type_introspection import TypeIntrospection
from graph.node_graph_coordinator import NodeGraphCoordinator

LINE_HEIGHT = 24
NODE_WIDTH = 190

FieldRole = Literal["pk", "fk", "pk_fk", "field"]
Cardinality = Literal["one", "zero_one", "one_many", "zero_many"]


def _port_slug(entity_id: str, field_key: str) -> str:
    stem = f"{entity_id}_{field_key}".replace(".", "_").replace(" ", "_")
    return f"p_{stem}"


@dataclass(frozen=True)
class ErdFieldSpec:
    """
    One visible ERD table row.

    AI-CORE-BEGIN
    ROLE: Preserve relational-table semantics for one field row before X6 serialization.
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
    """Non-relation model fields as ERD rows; ``id`` is treated as the primary key."""
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


def erd_payload_from_coordinator_for_domain(
    coordinator: NodeGraphCoordinator,
    domain_cls: type[BaseDomain],
) -> ErdGraphPayload:
    """
    Read the coordinator graph for one bounded context and assemble transient ERD rows.

    AI-CORE-BEGIN
    ROLE: Read interchange ``Entity`` vertices and ``entity_relation`` associations into transient ERD rows.
    CONTRACT: Runs after ``coordinator.build``; retains only entities declaring ``domain_cls`` via interchange domain edge target id matching ``TypeIntrospection.full_qualname(domain_cls)``.
    INVARIANTS: Relationship rows exist only when both entity interchange ids belong to that entity set (internal associations only).
    AI-CORE-END
    """
    domain_qual = TypeIntrospection.full_qualname(domain_cls)
    by_id: dict[str, EntityGraphNode] = {}

    for node in coordinator.get_all_nodes():
        if not isinstance(node, EntityGraphNode):
            continue
        if node.domain.target_node_id != domain_qual:
            continue
        by_id[node.node_id] = node

    entity_ids = frozenset(by_id)
    field_map: dict[str, dict[str, ErdFieldSpec]] = {}
    for eid in sorted(entity_ids):
        fields = entity_fields_from_class(by_id[eid].node_obj)
        field_map[eid] = {f.name: f for f in fields}

    relation_rows: list[tuple[str, str, str, dict[str, Any]]] = []
    for src_id in sorted(entity_ids):
        ent_node = by_id[src_id]
        for assoc in ent_node.relations:
            tgt = assoc.target_node_id
            if tgt not in entity_ids:
                continue
            props = assoc.properties
            field_name = str(props.get("field_name", "") or "")
            relation_rows.append((src_id, tgt, field_name, props))

    relationships: list[ErdEdgeSpec] = []
    emitted_inverse_pairs: set[frozenset[tuple[str, str]]] = set()
    by_slot = {
        (src, field_name): (src, tgt, field_name, props)
        for src, tgt, field_name, props in relation_rows
        if field_name
    }
    for src_id, tgt, field_name, props in relation_rows:
        inv_entity_id = props.get("inverse_entity_id")
        inv_field = props.get("inverse_field")
        inverse_key = (
            frozenset({(src_id, field_name), (str(inv_entity_id), str(inv_field))})
            if isinstance(inv_entity_id, str) and isinstance(inv_field, str) and inv_field
            else None
        )
        if inverse_key is not None and inverse_key in emitted_inverse_pairs:
            continue

        chosen = (src_id, tgt, field_name, props)
        if inverse_key is not None and (inv := by_slot.get((inv_entity_id, inv_field))) is not None:
            this_card = str(props.get("cardinality", "") or "")
            inv_card = str(inv[3].get("cardinality", "") or "")
            if this_card == "many" and inv_card == "one":
                chosen = inv
            elif this_card == inv_card:
                chosen = min((src_id, tgt, field_name, props), inv, key=lambda row: (row[0], row[2]))
            emitted_inverse_pairs.add(inverse_key)

        c_src, c_tgt, c_field, c_props = chosen
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

    entities = tuple(
        ErdEntitySpec(
            id=eid,
            label=by_id[eid].node_obj.__name__,
            attributes=entity_attributes_from_class(by_id[eid].node_obj),
            fields=tuple(field_map[eid].values()),
            is_junction=sum(1 for f in field_map[eid].values() if "fk" in f.role) >= 2
            and sum(1 for f in field_map[eid].values() if f.role == "field") <= 3,
        )
        for eid in sorted(entity_ids)
    )
    return ErdGraphPayload(entities=entities, relationships=tuple(relationships))


def erd_document_from_coordinator_graph(
    coordinator: NodeGraphCoordinator,
    domain_cls: type[BaseDomain],
) -> dict[str, list[dict[str, Any]]]:
    """
    Read the current coordinator graph and immediately return an X6 ERD document.

    AI-CORE-BEGIN
    ROLE: Public graph-backed ERD serializer; it reads only the live coordinator graph.
    CONTRACT: Uses ``coordinator.get_all_nodes()`` at call time and serializes only the requested domain.
    OUTPUT: X6 ``fromJSON`` document consumed directly by ``write_erd_html``.
    AI-CORE-END
    """
    return erd_payload_to_x6_document(
        erd_payload_from_coordinator_for_domain(coordinator, domain_cls),
    )


def erd_payload_to_x6_document(payload: ErdGraphPayload) -> dict[str, list[dict[str, Any]]]:
    """
    Build an X6 ``fromJSON`` payload: ``{\"cells\": [ ... ]}``.

    Entity nodes use ``shape: \"er-rect\"`` (registered in ``erd_html``). Attribute rows are
    visible ``list`` ports for the ER-table look; relationships attach to table boundaries,
    not to individual field rows. Node ``x/y`` are placeholders; bootstrap runs ELK.

    LOD keeps ``lod_port_names`` / ``lod_port_types`` aligned with ``list`` port order (tooltip + labels).
    """
    cells: list[dict[str, Any]] = []
    entities = list(payload.entities)
    for ent in entities:
        fields = list(ent.fields)
        if not fields:
            attrs_dict = dict(ent.attributes)
            if "id" not in attrs_dict:
                fields.append(ErdFieldSpec(name="id", type="str", role="pk"))
            for pk, pv in attrs_dict.items():
                fields.append(ErdFieldSpec(name=str(pk), type=str(pv), role="pk" if pk == "id" else "field"))
        if not fields:
            fields = [ErdFieldSpec(name="—", type="—")]
        lod_names: list[str] = []
        lod_types: list[str] = []
        lod_roles: list[str] = []
        port_items: list[dict[str, Any]] = []
        field_lines: list[str] = []
        for fld in fields:
            typ = str(fld.type)
            role_label = {"pk": "PK", "fk": "FK", "pk_fk": "PK,FK", "field": ""}[fld.role]
            lod_names.append(str(fld.name))
            lod_types.append(typ)
            lod_roles.append(role_label)
            western = _port_slug(ent.id, fld.name)
            role_font_weight = "bold" if fld.role in {"pk", "pk_fk"} else "normal"
            port_items.append({
                "id": western,
                "group": "list",
                "attrs": {
                    "portRoleLabel": {"text": role_label},
                    "portNameLabel": {"text": str(fld.name), "fontWeight": role_font_weight},
                    "portTypeLabel": {"text": typ},
                },
            })
            ref = f" -> {fld.references}" if fld.references else ""
            field_lines.append(f"{role_label:5} {fld.name}: {typ}{ref}".strip())

        n_ports = len(fields)
        body_h = LINE_HEIGHT * (1 + n_ports)
        panel = {
            "kind": "entity",
            "id": ent.id,
            "label": ent.label,
            "attributes": "\n".join(field_lines),
            "junction": str(bool(ent.is_junction)),
        }
        cells.append({
            "shape": "er-rect",
            "id": ent.id,
            "x": 12.0,
            "y": 12.0,
            "width": NODE_WIDTH,
            "height": float(body_h),
            "attrs": {"label": {"text": ent.label, "fontWeight": "bold"}},
            "ports": {"items": port_items},
            "data": {
                "payload_panel": {k: _serialize_panel_value(v) if isinstance(v, dict) else str(v) for k, v in panel.items()},
                "lod_port_names": lod_names,
                "lod_port_types": lod_types,
                "lod_port_roles": lod_roles,
                "erd_entity_kind": "junction" if ent.is_junction else "entity",
            },
        })

    for rel in payload.relationships:
        lp: list[dict[str, Any]] = []
        source_marker = _cardinality_marker(rel.source_cardinality)
        target_marker = _cardinality_marker(rel.target_cardinality)
        lp.append({
            "attrs": {"label": {"text": source_marker, "fontSize": 12, "fontWeight": "bold", "fill": "#111827"}},
            "position": {"distance": 0.08, "offset": {"y": -10}},
        })
        lp.append({
            "attrs": {"label": {"text": target_marker, "fontSize": 12, "fontWeight": "bold", "fill": "#111827"}},
            "position": {"distance": 0.92, "offset": {"y": -10}},
        })
        if rel.source == rel.target:
            source_spec = {"cell": rel.source, "anchor": {"name": "right"}}
            target_spec = {"cell": rel.target, "anchor": {"name": "right"}}
        else:
            source_spec = {"cell": rel.source, "anchor": {"name": "right"}}
            target_spec = {"cell": rel.target, "anchor": {"name": "left"}}

        epanel = {
            "kind": "relationship",
            "id": rel.id,
            "source": rel.source,
            "target": rel.target,
            "label": rel.label,
            "source_field": rel.source_field,
            "target_field": rel.target_field,
            "source_cardinality": rel.source_cardinality,
            "target_cardinality": rel.target_cardinality,
            "relationship_kind": rel.relationship_kind,
        }
        cells.append({
            "shape": "edge",
            "id": rel.id,
            "source": source_spec,
            "target": target_spec,
            "router": {"name": "orth"},
            "connector": {"name": "rounded", "args": {"radius": 4}},
            "attrs": {
                "line": {
                    "stroke": "#374151",
                    "strokeWidth": 1.4,
                    "targetMarker": None,
                    "sourceMarker": None,
                }
            },
            "labels": lp,
            "data": {"payload_panel": {k: str(v) for k, v in epanel.items()}, "erd_source_field": rel.source_field},
        })

    return {"cells": cells}


def _serialize_panel_value(value: Any) -> str:
    if isinstance(value, dict):
        parts = [f"{k}: {v}" for k, v in sorted(value.items())]
        return "\n".join(parts) if parts else ""
    return str(value)


def _cardinality_marker(cardinality: str) -> str:
    return {
        "one": "||",
        "zero_one": "o|",
        "one_many": "|<",
        "zero_many": "o<",
    }.get(cardinality, "")


def build_demo_erd_payload() -> ErdGraphPayload:
    """Small sample diagram (customer / order / line) for smoke runs and ``__main__``."""
    return ErdGraphPayload(
        entities=(
            ErdEntitySpec(
                id="entity.customer",
                label="Customer",
                attributes={"email": "string", "status": "enum"},
            ),
            ErdEntitySpec(
                id="entity.order",
                label="Order",
                attributes={"placed_at": "datetime", "total": "decimal"},
            ),
            ErdEntitySpec(
                id="entity.order_line",
                label="OrderLine",
                attributes={"sku": "string", "qty": "int"},
            ),
        ),
        relationships=(
            ErdEdgeSpec(
                id="rel.cust_orders",
                source="entity.customer",
                target="entity.order",
                label="1 — * orders",
                source_field="orders",
            ),
            ErdEdgeSpec(
                id="rel.order_lines",
                source="entity.order",
                target="entity.order_line",
                label="1 — * order_lines",
                source_field="order_lines",
            ),
        ),
    )
