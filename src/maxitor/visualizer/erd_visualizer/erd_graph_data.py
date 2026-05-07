# src/maxitor/visualizer/erd_visualizer/erd_graph_data.py
"""
Pure data layer for ERD-style graphs — no runtime / no HTML.

Produces an AntV **X6** graph document (``{ "cells": [...] }``) for :mod:`erd_html`.
Can derive payload from a built :class:`~graph.node_graph_coordinator.NodeGraphCoordinator`
plus a :class:`~action_machine.domain.base_domain.BaseDomain` subclass (interchange graph is
the source of entities and ``entity_relation`` edges; attributes come from Pydantic fields,
excluding relation slots).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Annotated, Any, get_args, get_origin

from action_machine.domain.base_domain import BaseDomain
from action_machine.domain.entity import BaseEntity
from action_machine.graph_model.nodes.entity_graph_node import EntityGraphNode
from action_machine.intents.entity.entity_intent_resolver import EntityIntentResolver
from action_machine.system_core.type_introspection import TypeIntrospection
from graph.node_graph_coordinator import NodeGraphCoordinator

LINE_HEIGHT = 24
NODE_WIDTH = 150


def _port_slug(entity_id: str, field_key: str) -> str:
    stem = f"{entity_id}_{field_key}".replace(".", "_").replace(" ", "_")
    return f"p_{stem}"


@dataclass(frozen=True)
class ErdEntitySpec:
    """One ERD entity (human label + optional attribute name → type map)."""

    id: str
    label: str
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ErdEdgeSpec:
    """Directed association between two entity node ids."""

    id: str
    source: str
    target: str
    label: str = ""
    #: Relation field name on ``source`` (used for FK row + east-side port anchoring).
    source_field: str = ""


@dataclass
class ErdGraphPayload:
    """Typed ERD specs before conversion to X6 cell JSON."""

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


def erd_payload_from_coordinator_for_domain(
    coordinator: NodeGraphCoordinator,
    domain_cls: type[BaseDomain],
) -> ErdGraphPayload:
    """
    Build :class:`ErdGraphPayload` from a coordinator graph for one bounded context.

    AI-CORE-BEGIN
    ROLE: Project interchange ``Entity`` vertices and ``entity_relation`` associations into flat ERD records.
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
    entities = tuple(
        ErdEntitySpec(
            id=eid,
            label=by_id[eid].node_obj.__name__,
            attributes=entity_attributes_from_class(by_id[eid].node_obj),
        )
        for eid in sorted(entity_ids)
    )

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
        if label_field:
            label = label_field if not cardinality else f"{label_field} ({cardinality})"
            rid_field = label_field
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
            ),
        )

    return ErdGraphPayload(entities=entities, relationships=tuple(relationships))


def erd_payload_to_x6_document(payload: ErdGraphPayload) -> dict[str, list[dict[str, Any]]]:
    """
    Build an X6 ``fromJSON`` payload: ``{\"cells\": [ ... ]}``.

    Entity nodes use ``shape: \"er-rect\"`` (registered in ``erd_html``). Attribute rows are
    visible ``list`` ports for the ER-table look; relationships attach to table boundaries,
    not to individual field rows. Node ``x/y`` are placeholders; bootstrap runs ELK.

    LOD stores type strings aligned with rows (``data.lod_port_types``, west-only order).
    """
    cells: list[dict[str, Any]] = []
    entities = list(payload.entities)
    lookup = {ent.id: ent for ent in entities}
    fk_extras: dict[str, dict[str, str]] = {ent.id: {} for ent in entities}
    for rel in payload.relationships:
        if not rel.source_field:
            continue
        tn = lookup.get(rel.target)
        lbl = f"FK → {tn.label}" if tn else "FK → ?"
        fk_extras.setdefault(rel.source, {})[rel.source_field] = lbl

    for ent in entities:
        attrs_dict = dict(ent.attributes)
        for fname, fv in fk_extras.get(ent.id, {}).items():
            if not fname:
                continue
            attrs_dict.setdefault(fname, fv)
        if not attrs_dict:
            attrs_dict = {"—": "—"}
        lod_types: list[str] = []
        port_items: list[dict[str, Any]] = []
        for pk, pv in attrs_dict.items():
            typ = str(pv)
            lod_types.append(typ)
            western = _port_slug(ent.id, pk)
            port_items.append({
                "id": western,
                "group": "list",
                "attrs": {
                    "portNameLabel": {"text": str(pk)},
                    "portTypeLabel": {"text": typ},
                },
            })

        n_ports = len(attrs_dict)
        body_h = LINE_HEIGHT * (1 + n_ports)
        panel = {
            "kind": "entity",
            "id": ent.id,
            "label": ent.label,
            "attributes": _serialize_panel_value(attrs_dict),
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
                "lod_port_types": lod_types,
            },
        })

    for ix, rel in enumerate(payload.relationships):
        lp: list[dict[str, Any]] = []
        if rel.label:
            lp.append({
                "attrs": {"label": {"text": rel.label, "fontSize": 9, "fill": "#334155"}},
                "position": {"distance": 0.5, "offset": {"y": 18 if ix % 2 else -18}},
            })

        source_spec: dict[str, Any] = {"cell": rel.source, "anchor": {"name": "right"}}
        target_spec: dict[str, Any] = {"cell": rel.target, "anchor": {"name": "left"}}

        epanel = {
            "kind": "relationship",
            "id": rel.id,
            "source": rel.source,
            "target": rel.target,
            "label": rel.label,
            "source_field": rel.source_field,
        }
        cells.append({
            "shape": "edge",
            "id": rel.id,
            "source": source_spec,
            "target": target_spec,
            "attrs": {"line": {"stroke": "#A2B1C3", "strokeWidth": 2}},
            "labels": lp,
            "data": {"payload_panel": {k: str(v) for k, v in epanel.items()}, "erd_source_field": rel.source_field},
        })

    return {"cells": cells}


def _serialize_panel_value(value: Any) -> str:
    if isinstance(value, dict):
        parts = [f"{k}: {v}" for k, v in sorted(value.items())]
        return "\n".join(parts) if parts else ""
    return str(value)


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
