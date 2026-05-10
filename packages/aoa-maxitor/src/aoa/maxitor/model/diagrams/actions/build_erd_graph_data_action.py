# packages/aoa-maxitor/src/aoa/maxitor/model/diagrams/actions/build_erd_graph_data_action.py
# mypy: ignore-errors
# pylint: disable=too-many-branches,too-many-statements
"""
ERD graph materialization — pure helpers for coordinator → JSON payloads.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Pure helpers read :class:`~aoa.graph.node_graph_coordinator.NodeGraphCoordinator`
and build normalized ERD rows (:class:`ErdGraphPayload`) and ``nodes`` / ``edges`` JSON.

HTTP-facing flows use small actions (``ListErdDomainQualnamesAction``,
``GetErdDomainPayloadAction``) with ``@connection`` on :class:`~aoa.maxitor.model.core.resources.service_graph_resource.ServiceGraphResource`;
this module keeps serializers shared with the Maxitor React ERD viewer (``nodes`` / ``edges`` JSON).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Annotated, Any, Literal, get_args, get_origin

from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.domain.entity import BaseEntity
from aoa.action_machine.graph_model.nodes.entity_graph_node import EntityGraphNode
from aoa.action_machine.intents.entity.entity_intent_resolver import EntityIntentResolver
from aoa.action_machine.system_core.type_introspection import TypeIntrospection
from aoa.graph.node_graph_coordinator import NodeGraphCoordinator
from aoa.maxitor.model.core.actions.load_graph_action import MAXITOR_NX_GRAPH_COORDINATOR_KEY

# Matches the React ERD viewer entity disk palette order for consistent demos.
_DOMAIN_ACCENT_PALETTE: tuple[str, ...] = (
    "#3b82f6",
    "#8b5cf6",
    "#10b981",
    "#f59e0b",
    "#ef4444",
    "#06b6d4",
    "#ec4899",
    "#64748b",
)


def _domain_qual_to_accent(nodes: list[EntityGraphNode]) -> dict[str, str]:
    """Stable accent colour per declared ``domain.target_node_id`` qualifier."""
    quals = sorted({n.domain.target_node_id for n in nodes})
    return {q: _DOMAIN_ACCENT_PALETTE[i % len(_DOMAIN_ACCENT_PALETTE)] for i, q in enumerate(quals)}


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
    #: Header/table accent (hex). Empty → HTML export falls back to row-index palette.
    accent_color: str = ""
    #: Declared interchange domain qualifier (``TypeIntrospection.full_qualname(domain_cls)``).
    declaring_domain_qual: str = ""


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
    accent_by_qual = _domain_qual_to_accent(list(all_graph.values()))

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
            accent_color=accent_by_qual.get(all_graph[eid].domain.target_node_id, ""),
            declaring_domain_qual=all_graph[eid].domain.target_node_id,
        )
        for eid in sorted(display_ids)
    )
    return ErdGraphPayload(entities=entities, relationships=tuple(relationships))


ERD_DEFAULT_ENTITY_COLORS: tuple[str, ...] = _DOMAIN_ACCENT_PALETTE


def _role_to_flags(role: str) -> dict[str, bool]:
    """Convert a field role string into boolean flags for JS."""
    return {
        "primary_key": role in ("pk", "pk_fk"),
        "foreign_key": role in ("fk", "pk_fk"),
    }


def _serialize_entity(entity: ErdEntitySpec, color: str) -> dict[str, Any]:
    """Convert ErdEntitySpec into the JS node shape (shared with the React ERD viewer ``ERD_DATA`` JSON)."""
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
    qual = (getattr(entity, "declaring_domain_qual", None) or "").strip()
    out: dict[str, Any] = {
        "id": entity.id,
        "label": entity.label,
        "color": color,
        "fields": fields,
    }
    if qual:
        out["domain_qualifier"] = qual

    return out


def _serialize_edge(rel: ErdEdgeSpec) -> dict[str, Any]:
    """Convert ErdEdgeSpec into the JS edge shape."""
    return {
        "source": rel.source,
        "target": rel.target,
        "label": rel.label or "",
    }


def payload_to_domain_dict(payload: ErdGraphPayload) -> dict[str, Any]:
    """Convert ErdGraphPayload into the JSON-ready domain dictionary for ``ERD_DATA``."""
    nodes: list[dict[str, Any]] = []
    for i, entity in enumerate(payload.entities):
        accent = (getattr(entity, "accent_color", None) or "").strip()
        color = accent if accent else ERD_DEFAULT_ENTITY_COLORS[i % len(ERD_DEFAULT_ENTITY_COLORS)]
        nodes.append(_serialize_entity(entity, color))

    edges = [_serialize_edge(rel) for rel in payload.relationships]
    return {"nodes": nodes, "edges": edges}


def node_graph_coordinator_from_interchange_nx(nx_graph: Any) -> NodeGraphCoordinator:
    """Recover the coordinator embedded by :class:`~aoa.maxitor.model.core.actions.load_graph_action.LoadGraphAction`."""
    gdict = getattr(nx_graph, "graph", None)
    if not isinstance(gdict, dict):
        msg = "nx_graph must be a NetworkX graph with a mapping ``graph`` attribute."
        raise TypeError(msg)
    coordinator = gdict.get(MAXITOR_NX_GRAPH_COORDINATOR_KEY)
    if coordinator is None:
        msg = (
            f"Interchange nx_graph is missing coordinator under {MAXITOR_NX_GRAPH_COORDINATOR_KEY!r}; "
            "materialize it with LoadGraphAction.Params(graph=coordinator) first."
        )
        raise ValueError(msg)
    return coordinator
