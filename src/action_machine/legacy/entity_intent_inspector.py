# src/action_machine/legacy/entity_intent_inspector.py
"""
``EntityIntentInspector`` — intent **inspector** for ``@entity`` classes.

Walks ``EntityIntent`` subclasses and, when ``entity_info_is_set()`` holds,
materializes a coordinator **facet** as ``FacetVertex`` (description, domain,
scalar fields, relations, lifecycles). This is the canonical place to derive
entity facet tuples from Pydantic ``model_fields`` plus relation/lifecycle
annotations.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Turn declared entity models into **structured node metadata** for the shared
``GraphCoordinator`` graph without a separate “entity coordinator” or ad hoc
collector layer. The inspector plugs into the same pipeline as other facet
inspectors (actions, checkers, …).

═══════════════════════════════════════════════════════════════════════════════
SCOPE (IN / OUT)
═══════════════════════════════════════════════════════════════════════════════

**In scope**
    ``collect_entity_info``, ``collect_entity_fields``, ``collect_entity_relations``,
    ``collect_entity_lifecycles`` — read ``_entity_info`` and ``model_fields`` and
    return frozen-friendly snapshot dataclasses.
    ``EntityIntentInspector.inspect`` / ``facet_snapshot_for_class`` — produce
    ``FacetVertex`` with ``node_type="Entity"`` and optional ``edges``:
    informational ``belongs_to`` → ``Domain`` when a domain type is known, plus
    relation edges to related ``Entity`` interchange vertices (skipped when ``NoGraphEdge()``
    is set on the field).

    When ``_meta_info`` is present (same shape as ``@meta``), ``description`` and
    ``domain`` for the facet override / extend ``@entity`` scratch so the graph
    matches action-style meta without duplicating decorator implementations.

**Out of scope**
    ORM loading or hydrating relation containers.

═══════════════════════════════════════════════════════════════════════════════
TERMINOLOGY (USE CONSISTENTLY)
═══════════════════════════════════════════════════════════════════════════════

**Intent** — ``EntityIntent`` marks classes that declare the ``@entity`` grammar.
**Decorator** — ``@entity`` writes **scratch** (``_entity_info``).
**Inspector** — this module’s class, paired with that intent marker.
**Gate coordinator** — after ``register(...).build()``, holds the facet graph;
``Core`` registers ``EntityIntentInspector`` on the default
coordinator setup.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    @entity  ──>  _entity_info  (scratch on class)
         │
         │  entity_info_is_set(cls)
         v
    EntityIntentInspector.inspect(cls)
         │
         ├─ collect_entity_info / fields / relations / lifecycles
         │
         v
    Snapshot.to_facet_vertex()  ──>  FacetVertex(node_type="Entity", edges=…)
    (``belongs_to`` domain + Entity→Entity relation edges)

═══════════════════════════════════════════════════════════════════════════════
RATIONALE
═══════════════════════════════════════════════════════════════════════════════

Centralizing ``collect_entity_*`` here avoids duplicating Pydantic introspection
for entities and keeps facet shape aligned with ``FacetVertex`` tuples. The
public functions are stable hooks for **tests** and optional tooling without
pulling the whole coordinator.

═══════════════════════════════════════════════════════════════════════════════
LIFECYCLE (IMPORT VS BUILD VS RUNTIME)
═══════════════════════════════════════════════════════════════════════════════

- **Import**: entity classes and inspector class are defined.
- **Coordinator ``build()``**: inspector runs over registered targets and emits
  facet payloads.
- **Runtime**: domain entities are data; this module does not run per request.
"""

from __future__ import annotations

import inspect
import types
import typing
from dataclasses import dataclass, field
from typing import Annotated, Any, get_args, get_origin

from pydantic.fields import FieldInfo
from pydantic_core import PydanticUndefined

from action_machine.domain.lifecycle import Lifecycle, StateInfo, StateType
from action_machine.domain.relation_containers import BaseRelationMany, BaseRelationOne
from action_machine.domain.relation_markers import Inverse, NoGraphEdge, NoInverse, Rel
from action_machine.intents.entity.entity_intent import EntityIntent, entity_info_is_set
from action_machine.legacy.interchange_vertex_labels import DOMAIN_VERTEX_TYPE, ENTITY_VERTEX_TYPE
from graph.base_facet_snapshot import BaseFacetSnapshot
from graph.base_intent_inspector import BaseIntentInspector, FacetInspectResult
from graph.facet_edge import FacetEdge
from graph.facet_vertex import FacetVertex

# ─────────────────────────────────────────────────────────────────────────────
# Scalar field constraints (aligned with Params/Result facet extraction)
# ─────────────────────────────────────────────────────────────────────────────

_ENTITY_CONSTRAINT_ATTRS: tuple[str, ...] = (
    "gt", "ge", "lt", "le",
    "min_length", "max_length",
    "pattern",
    "multiple_of",
    "strict",
)


def _extract_entity_field_constraints(field_info: FieldInfo) -> dict[str, Any]:
    """
    Pull Pydantic constraint-like data from ``FieldInfo`` for entity scalars.

    Reads direct ``FieldInfo`` attributes and items in ``metadata``.

    Args:
        field_info: Pydantic field descriptor from ``model_fields``.

    Returns:
        Dict of non-null constraints; empty if none found.
    """
    constraints: dict[str, Any] = {}
    for attr in _ENTITY_CONSTRAINT_ATTRS:
        value = getattr(field_info, attr, None)
        if value is not None:
            constraints[attr] = value
    for meta_item in field_info.metadata or []:
        for attr in _ENTITY_CONSTRAINT_ATTRS:
            value = getattr(meta_item, attr, None)
            if value is not None and attr not in constraints:
                constraints[attr] = value
    return constraints


# ─────────────────────────────────────────────────────────────────────────────
# Public materialization helpers (also used by EntityIntentInspector)
# ─────────────────────────────────────────────────────────────────────────────


def collect_entity_info(cls: type) -> EntityInfo | None:
    """
    Read ``_entity_info`` from ``cls`` (MRO-aware via ``getattr``).

    Args:
        cls: Entity class decorated with ``@entity``.

    Returns:
        ``EntityInfo`` or ``None`` if ``_entity_info`` is missing.
    """
    entity_info: dict[str, Any] | None = getattr(cls, "_entity_info", None)
    if entity_info is None:
        return None
    description = entity_info["description"]
    domain = entity_info.get("domain")
    meta_info = getattr(cls, "_meta_info", None)
    if isinstance(meta_info, dict):
        meta_desc = meta_info.get("description")
        if isinstance(meta_desc, str) and meta_desc.strip():
            description = meta_desc.strip()
        if "domain" in meta_info:
            domain = meta_info["domain"]
    return EntityInfo(description=description, domain=domain)


def _is_lifecycle_subclass(annotation: Any) -> bool:
    """
    Whether ``annotation`` (possibly ``Annotated`` / optional union) refers to a
    ``Lifecycle`` subclass.
    """
    if get_origin(annotation) is Annotated:
        base = get_args(annotation)[0]
        return _is_lifecycle_subclass(base)

    if isinstance(annotation, type) and issubclass(annotation, Lifecycle):
        return True

    origin = get_origin(annotation)
    if origin is types.UnionType or origin is typing.Union:
        for arg in get_args(annotation):
            if arg is types.NoneType:
                continue
            if _is_lifecycle_subclass(arg):
                return True
        return False

    return False


def _extract_lifecycle_class(annotation: Any) -> type | None:
    """Resolve the concrete ``Lifecycle`` subclass from a field annotation."""
    if get_origin(annotation) is Annotated:
        base = get_args(annotation)[0]
        return _extract_lifecycle_class(base)

    if isinstance(annotation, type) and issubclass(annotation, Lifecycle):
        return annotation

    origin = get_origin(annotation)
    if origin is types.UnionType or origin is typing.Union:
        for arg in get_args(annotation):
            if arg is types.NoneType:
                continue
            result = _extract_lifecycle_class(arg)
            if result is not None:
                return result

    return None


def _is_relation_container(annotation: Any) -> bool:
    """
    True if ``annotation`` denotes ``BaseRelationOne`` / ``BaseRelationMany``
    (including inside ``Optional`` / ``Annotated``).
    """
    if get_origin(annotation) is Annotated:
        base = get_args(annotation)[0]
        return _is_relation_container(base)

    origin = get_origin(annotation)
    if origin is types.UnionType or origin is typing.Union:
        for arg in get_args(annotation):
            if arg is types.NoneType:
                continue
            if _is_relation_container(arg):
                return True
        return False

    if origin is not None and inspect.isclass(origin):
        if issubclass(origin, (BaseRelationOne, BaseRelationMany)):
            return True

    if isinstance(annotation, type) and issubclass(
        annotation, (BaseRelationOne, BaseRelationMany)
    ):
        return True

    return False


def collect_entity_fields(cls: type) -> list[EntityFieldInfo]:  # pylint: disable=too-many-branches
    """
    Collect scalar entity fields from ``model_fields``.

    Skips relation containers and ``Lifecycle``-typed fields.

    Args:
        cls: Entity class with ``@entity``.

    Returns:
        List of ``EntityFieldInfo``; empty if ``model_fields`` is missing.
    """
    model_fields = getattr(cls, "model_fields", None)
    if not model_fields:
        return []

    try:
        from typing_extensions import get_type_hints  # pylint: disable=import-outside-toplevel

        hints = get_type_hints(cls, include_extras=True)
    except Exception:
        hints = {}

    fields: list[EntityFieldInfo] = []

    for field_name, field_info in model_fields.items():
        annotation = hints.get(field_name, field_info.annotation)

        if _is_relation_container(annotation):
            continue

        if _is_lifecycle_subclass(field_info.annotation):
            continue

        raw_annotation = field_info.annotation
        field_type_str = str(raw_annotation) if raw_annotation is not None else "Any"
        if raw_annotation is not None and hasattr(raw_annotation, "__name__"):
            field_type_str = raw_annotation.__name__

        description = field_info.description or ""
        constraints = _extract_entity_field_constraints(field_info)
        is_required = field_info.is_required()
        default = field_info.default if not is_required else PydanticUndefined
        deprecated = bool(getattr(field_info, "deprecated", False))

        fields.append(EntityFieldInfo(
            field_name=field_name,
            field_type=field_type_str,
            description=description,
            required=is_required,
            default=default,
            constraints=constraints,
            deprecated=deprecated,
        ))

    return fields


def _extract_relation_info(  # pylint: disable=too-many-branches
    field_name: str,
    annotation: Any,
    field_info: FieldInfo,
) -> EntityRelationInfo | None:
    """
    Parse ``Annotated[..., Inverse | NoInverse, NoGraphEdge?, ...]`` plus container type into
    ``EntityRelationInfo``.

    Args:
        field_name: Model field name.
        annotation: Full annotation (may include ``Annotated`` / unions).
        field_info: Pydantic ``FieldInfo``.

    Returns:
        ``EntityRelationInfo`` or ``None`` if no relation container is found.
    """
    base_type = annotation
    annotated_metadata: tuple[Any, ...] = ()

    if get_origin(annotation) is Annotated:
        args = get_args(annotation)
        base_type = args[0]
        annotated_metadata = tuple(args[1:])

    unwrapped = base_type
    origin = get_origin(base_type)
    if origin is types.UnionType or origin is typing.Union:
        for arg in get_args(base_type):
            if arg is not types.NoneType:
                unwrapped = arg
                break
    base_type = unwrapped

    origin = get_origin(base_type)
    container_class = None

    if origin is not None and inspect.isclass(origin) and issubclass(
        origin, (BaseRelationOne, BaseRelationMany)
    ):
        container_class = origin
    elif isinstance(base_type, type) and issubclass(
        base_type, (BaseRelationOne, BaseRelationMany)
    ):
        container_class = base_type

    if container_class is None:
        return None

    target_entity = None
    container_args = get_args(base_type)
    if container_args and isinstance(container_args[0], type):
        target_entity = container_args[0]
    if target_entity is None:
        return None

    relation_type = container_class.relation_type.value
    cardinality = "one" if issubclass(container_class, BaseRelationOne) else "many"

    has_inverse = False
    inverse_entity = None
    inverse_field = None
    for item in annotated_metadata:
        if isinstance(item, Inverse):
            has_inverse = True
            inverse_entity = item.target_entity
            inverse_field = item.field_name
            break
        if isinstance(item, NoInverse):
            break

    description = ""
    default_val = field_info.default
    if isinstance(default_val, Rel):
        description = default_val.description
    elif field_info.description:
        description = field_info.description

    deprecated = bool(getattr(field_info, "deprecated", False))
    omit_graph_edge = any(isinstance(item, NoGraphEdge) for item in annotated_metadata)

    return EntityRelationInfo(
        field_name=field_name,
        container_class=container_class,
        relation_type=relation_type,
        target_entity=target_entity,
        cardinality=cardinality,
        description=description,
        has_inverse=has_inverse,
        inverse_entity=inverse_entity,
        inverse_field=inverse_field,
        deprecated=deprecated,
        omit_graph_edge=omit_graph_edge,
    )


def collect_entity_relations(cls: type) -> list[EntityRelationInfo]:
    """
    Collect relation fields from ``model_fields``.

    Args:
        cls: Entity class with ``@entity``.

    Returns:
        List of ``EntityRelationInfo``.
    """
    model_fields = getattr(cls, "model_fields", None)
    if not model_fields:
        return []

    try:
        from typing_extensions import get_type_hints  # pylint: disable=import-outside-toplevel

        hints = get_type_hints(cls, include_extras=True)
    except Exception:
        hints = {}

    relations: list[EntityRelationInfo] = []

    for field_name, field_info in model_fields.items():
        annotation = hints.get(field_name, field_info.annotation)

        if not _is_relation_container(annotation):
            continue

        rel_info = _extract_relation_info(field_name, annotation, field_info)
        if rel_info is not None:
            relations.append(rel_info)

    return relations


def lifecycle_state_vertex_type(state_info: StateInfo) -> str:
    """
    Interchange ``node_type`` for one lifecycle state (initial / intermediate / final).

    Drives distinct icons and fills in the graph visualizer.
    """
    t = state_info.state_type
    if t == StateType.INITIAL:
        return "lifecycle_state_initial"
    if t == StateType.INTERMEDIATE:
        return "lifecycle_state_intermediate"
    return "lifecycle_state_final"


def lifecycle_state_node_name(
    entity_class: type,
    field_name: str,
    lifecycle_class: type,
    state_key: str,
) -> str:
    """
    Globally unique interchange vertex id for one state **on a concrete entity field**.

    Scoped by ``entity_class`` + ``field_name`` so two entities may reuse the same
    ``Lifecycle`` subclass (and state keys) without graph key collisions.

    Shape: full entity path + ``:`` + ``{field}:{lifecycle_short}:{state_key}``
    (via :meth:`~graph.base_intent_inspector.BaseIntentInspector._make_node_name`).
    """
    return BaseIntentInspector._make_node_name(
        entity_class,
        f"{field_name}:{lifecycle_class.__name__}:{state_key}",
    )


def entity_relation_facet_edge_type(relation_type: str, cardinality: str) -> str:
    """
    Facet ``edge_type`` string for :class:`~graph.facet_edge.FacetEdge`.

    Maps to interchange ``COMPOSITION_*`` / ``AGGREGATION_*`` / ``ASSOCIATION_*`` via
    :data:`graph.graph_builder` tables.
    """
    rt = str(relation_type).lower()
    card = str(cardinality).lower()
    if rt not in frozenset({"composition", "aggregation", "association"}):
        msg = f"unknown entity relation_type {relation_type!r}"
        raise ValueError(msg)
    if card not in frozenset({"one", "many"}):
        msg = f"unknown entity relation cardinality {cardinality!r}"
        raise ValueError(msg)
    return f"entity_{rt}_{card}"


def collect_entity_lifecycles(cls: type) -> list[EntityLifecycleInfo]:
    """
    Collect fields whose type is a specialized ``Lifecycle`` with ``_template``.

    Args:
        cls: Entity class with ``@entity``.

    Returns:
        ``EntityLifecycleInfo`` entries for fields whose class exposes a non-null
        ``_get_template()``.
    """
    model_fields = getattr(cls, "model_fields", None)
    if not model_fields:
        return []

    lifecycles: list[EntityLifecycleInfo] = []

    for field_name, field_info in model_fields.items():
        annotation = field_info.annotation

        if not _is_lifecycle_subclass(annotation):
            continue

        lifecycle_class = _extract_lifecycle_class(annotation)
        if lifecycle_class is None:
            continue

        template = None
        if hasattr(lifecycle_class, "_get_template"):
            template = lifecycle_class._get_template()

        if template is None:
            continue

        states = template.get_states()
        initial_keys = template.get_initial_keys()
        final_keys = template.get_final_keys()

        lifecycles.append(EntityLifecycleInfo(
            field_name=field_name,
            lifecycle_class=lifecycle_class,
            template_ref=template,
            state_count=len(states),
            initial_count=len(initial_keys),
            final_count=len(final_keys),
        ))

    return lifecycles


class EntityIntentInspector(BaseIntentInspector):
    """
AI-CORE-BEGIN
    ROLE: Concrete ``EntityIntent`` inspector.
    CONTRACT: Emit ``entity`` facet nodes plus relation edges to target entities.
    INVARIANTS: Storage key is stable (``entity``); collection remains declaring-class metadata only.
    AI-CORE-END
"""

    _target_intent: type = EntityIntent

    @dataclass(frozen=True)
    class Snapshot(BaseFacetSnapshot):
        """Frozen facet snapshot before tuple encoding for ``FacetVertex``."""

        @dataclass(frozen=True)
        class EntityInfo:
            """Facet description and optional domain (``@entity`` + optional ``_meta_info``)."""

            description: str
            domain: Any = None

        @dataclass(frozen=True)
        class EntityFieldInfo:
            """Scalar model field metadata for the entity facet."""

            field_name: str
            field_type: str
            description: str
            required: bool
            default: Any
            constraints: dict[str, Any] = field(default_factory=dict)
            deprecated: bool = False

        @dataclass(frozen=True)
        class EntityRelationInfo:
            """Relation field: container type, cardinality, inverse markers, etc."""

            field_name: str
            container_class: type
            relation_type: str
            target_entity: type
            cardinality: str
            description: str
            has_inverse: bool
            inverse_entity: type | None = None
            inverse_field: str | None = None
            deprecated: bool = False
            omit_graph_edge: bool = False

        @dataclass(frozen=True)
        class EntityLifecycleInfo:
            """Lifecycle field with template statistics."""

            field_name: str
            lifecycle_class: type
            template_ref: Any
            state_count: int
            initial_count: int
            final_count: int

        class_ref: type
        entity_info: EntityInfo
        entity_fields: tuple[EntityFieldInfo, ...]
        entity_relations: tuple[EntityRelationInfo, ...]
        entity_lifecycles: tuple[EntityLifecycleInfo, ...]

        def to_facet_vertex(
            self,
            *,
            entity_extra_edges: tuple[FacetEdge, ...] = (),
        ) -> FacetVertex:
            """Serialize this snapshot into a coordinator ``FacetVertex``."""
            fields_meta: tuple[tuple[Any, ...], ...] = tuple(
                (
                    item.field_name,
                    item.field_type,
                    item.description,
                    item.required,
                    item.default,
                    tuple(item.constraints.items()),
                    item.deprecated,
                )
                for item in self.entity_fields
            )
            relations_meta: tuple[tuple[Any, ...], ...] = tuple(
                (
                    item.field_name,
                    item.container_class,
                    item.relation_type,
                    item.target_entity,
                    item.cardinality,
                    item.description,
                    item.has_inverse,
                    item.inverse_entity,
                    item.inverse_field,
                    item.deprecated,
                    item.omit_graph_edge,
                )
                for item in self.entity_relations
            )
            lifecycles_meta: tuple[tuple[Any, ...], ...] = tuple(
                (
                    item.field_name,
                    item.lifecycle_class,
                    item.template_ref,
                    item.state_count,
                    item.initial_count,
                    item.final_count,
                )
                for item in self.entity_lifecycles
            )
            domain_edges: list[FacetEdge] = []
            dom = self.entity_info.domain
            if dom is not None and isinstance(dom, type):
                domain_edges.append(
                    EntityIntentInspector._make_edge(
                        target_node_type=DOMAIN_VERTEX_TYPE,
                        target_cls=dom,
                        edge_type="belongs_to",
                        is_structural=False,
                    ),
                )

            relation_edges: list[FacetEdge] = []
            for rel in self.entity_relations:
                if rel.omit_graph_edge:
                    continue
                facet_et = entity_relation_facet_edge_type(rel.relation_type, rel.cardinality)
                target_name = EntityIntentInspector._make_node_name(rel.target_entity)
                meta_pairs: list[tuple[str, Any]] = [
                    ("field_name", rel.field_name),
                    ("relation_type", rel.relation_type),
                    ("cardinality", rel.cardinality),
                    ("description", rel.description),
                    ("has_inverse", rel.has_inverse),
                ]
                if rel.inverse_entity is not None:
                    meta_pairs.append(
                        (
                            "inverse_entity",
                            EntityIntentInspector._make_node_name(rel.inverse_entity),
                        ),
                    )
                if rel.inverse_field:
                    meta_pairs.append(("inverse_field", rel.inverse_field))
                relation_edges.append(
                    FacetEdge(
                        target_node_type=ENTITY_VERTEX_TYPE,
                        target_name=target_name,
                        edge_type=facet_et,
                        is_structural=False,
                        edge_meta=tuple(meta_pairs),
                        target_class_ref=rel.target_entity,
                    ),
                )

            return FacetVertex(
                node_type=ENTITY_VERTEX_TYPE,
                node_name=EntityIntentInspector._make_node_name(self.class_ref),
                node_class=self.class_ref,
                node_meta=EntityIntentInspector._make_meta(
                    description=self.entity_info.description,
                    domain=self.entity_info.domain,
                    fields=fields_meta,
                    relations=relations_meta,
                    lifecycles=lifecycles_meta,
                ),
                edges=tuple(domain_edges + relation_edges + list(entity_extra_edges)),
            )

    @classmethod
    def _lifecycle_graph_payloads(
        cls,
        snap: Any,
    ) -> tuple[tuple[FacetEdge, ...], tuple[FacetVertex, ...]]:
        """
        Build ``entity_has_lifecycle`` edges for the entity row plus ``lifecycle`` /
        ``lifecycle_state_{initial,intermediate,final}`` facet payloads (states, initial links, transitions).

        Lifecycle nodes are **not** linked to the ``domain`` vertex; visualization
        puts them in the entity's domain bundle via ``HAS_LIFECYCLE`` /
        ``HAS_LIFECYCLE_STATE`` propagation from the entity's ``belongs_to`` edge.

        When there is more than one initial state, emit ``lifecycle_initial`` from
        the lifecycle node to each initial state. Otherwise initial states are only
        linked via ``lifecycle_contains_state``.
        """
        if not snap.entity_lifecycles:
            return (), ()

        entity_edges: list[FacetEdge] = []
        extras: list[FacetVertex] = []

        for lc in snap.entity_lifecycles:
            lc_field_name = lc.field_name
            lc_name = cls._make_node_name(snap.class_ref, lc_field_name)
            lc_cls = lc.lifecycle_class
            template = lc.template_ref
            states = template.get_states()
            initial_keys = template.get_initial_keys()

            entity_edges.append(
                FacetEdge(
                    target_node_type="lifecycle",
                    target_name=lc_name,
                    edge_type="entity_has_lifecycle",
                    is_structural=False,
                    edge_meta=(
                        ("field_name", lc_field_name),
                        ("lifecycle_class", lc_cls.__name__),
                    ),
                    target_class_ref=lc_cls,
                ),
            )

            def state_vertex_name(
                state_key: str,
                *,
                _field: str = lc_field_name,
                _lc_cls: type = lc_cls,
            ) -> str:
                return lifecycle_state_node_name(
                    snap.class_ref, _field, _lc_cls, state_key,
                )

            lc_edges: list[FacetEdge] = []

            for sk, st in states.items():
                lc_edges.append(
                    FacetEdge(
                        target_node_type=lifecycle_state_vertex_type(st),
                        target_name=state_vertex_name(sk),
                        edge_type="lifecycle_contains_state",
                        is_structural=False,
                        edge_meta=(
                            ("state_key", sk),
                            ("label", st.display_name),
                            ("state_type", st.state_type.value),
                        ),
                        target_class_ref=snap.class_ref,
                    ),
                )

            if len(initial_keys) > 1:
                for ik in sorted(initial_keys):
                    st_ik = states[ik]
                    lc_edges.append(
                        FacetEdge(
                            target_node_type=lifecycle_state_vertex_type(st_ik),
                            target_name=state_vertex_name(ik),
                            edge_type="lifecycle_initial",
                            is_structural=False,
                            edge_meta=(("state_key", ik),),
                            target_class_ref=snap.class_ref,
                        ),
                    )

            extras.append(
                FacetVertex(
                    node_type="lifecycle",
                    node_name=lc_name,
                    node_class=lc_cls,
                    node_meta=cls._make_meta(
                        field_name=lc_field_name,
                        entity_class=snap.class_ref,
                        state_count=len(states),
                        initial_count=len(initial_keys),
                        final_count=len(template.get_final_keys()),
                    ),
                    edges=tuple(lc_edges),
                ),
            )

            for sk, st in states.items():
                out_edges: list[FacetEdge] = []
                for tgt in sorted(st.transitions):
                    st_tgt = states[tgt]
                    out_edges.append(
                        FacetEdge(
                            target_node_type=lifecycle_state_vertex_type(st_tgt),
                            target_name=state_vertex_name(tgt),
                            edge_type="lifecycle_transition",
                            is_structural=False,
                            edge_meta=(
                                ("from_state", sk),
                                ("to_state", tgt),
                            ),
                            target_class_ref=snap.class_ref,
                        ),
                    )

                extras.append(
                    FacetVertex(
                        node_type=lifecycle_state_vertex_type(st),
                        node_name=state_vertex_name(sk),
                        node_class=snap.class_ref,
                        node_meta=cls._make_meta(
                            field_name=lc_field_name,
                            state_key=sk,
                            label=st.display_name,
                            state_type=st.state_type.value,
                        ),
                        edges=tuple(out_edges),
                    ),
                )

        return tuple(entity_edges), tuple(extras)

    @classmethod
    def _subclasses_recursive(cls) -> list[type]:
        """All direct and indirect subclasses of ``EntityIntent``."""
        return cls._collect_subclasses(cls._target_intent)

    @classmethod
    def _has_entity_info_invariant(cls, target_cls: type) -> bool:
        """True when ``@entity`` has written ``_entity_info`` on ``target_cls``."""
        return entity_info_is_set(target_cls)

    @classmethod
    def inspect(
        cls, target_cls: type,
    ) -> FacetInspectResult:
        """
        Build an entity facet payload (and optional ``lifecycle`` / ``lifecycle_state``
        facet rows when the model declares ``Lifecycle`` fields with templates).

        Args:
            target_cls: Candidate class.

        Returns:
            ``FacetVertex``, or a non-empty tuple whose first element is the entity
            row and the rest are lifecycle graph facets, or ``None`` when the class
            is not a decorated entity.
        """
        if not cls._has_entity_info_invariant(target_cls):
            return None
        snap = cls.facet_snapshot_for_class(target_cls)
        assert snap is not None
        entity_edges, extras = cls._lifecycle_graph_payloads(snap)
        entity_payload = snap.to_facet_vertex(entity_extra_edges=entity_edges)
        if not extras:
            return entity_payload
        return (entity_payload, *extras)

    @classmethod
    def facet_snapshot_for_class(
        cls, target_cls: type,
    ) -> Snapshot | None:
        """
        Materialize a typed ``Snapshot`` without encoding tuples for ``node_meta``.

        Returns:
            ``Snapshot`` or ``None`` if ``_entity_info`` is missing or
            ``collect_entity_info`` returns ``None``.
        """
        if not cls._has_entity_info_invariant(target_cls):
            return None
        entity_info = collect_entity_info(target_cls)
        entity_fields = collect_entity_fields(target_cls)
        entity_relations = collect_entity_relations(target_cls)
        entity_lifecycles = collect_entity_lifecycles(target_cls)
        if entity_info is None:
            return None
        return cls.Snapshot(
            class_ref=target_cls,
            entity_info=entity_info,
            entity_fields=tuple(entity_fields),
            entity_relations=tuple(entity_relations),
            entity_lifecycles=tuple(entity_lifecycles),
        )

    @classmethod
    def facet_snapshot_storage_key(
        cls, _target_cls: type, _payload: FacetVertex,
    ) -> str:
        """Storage bucket key for entity facet snapshots."""
        return "entity"

    @classmethod
    def should_register_facet_snapshot_for_vertex(
        cls,
        _target_cls: type,
        payload: FacetVertex,
    ) -> bool:
        """Only the primary ``Entity`` row hydrates the typed snapshot."""
        return payload.node_type == ENTITY_VERTEX_TYPE

    @classmethod
    def _build_payload(cls, target_cls: type) -> FacetVertex:
        """
        Wrap ``collect_entity_*`` results into ``FacetVertex``.

        Args:
            target_cls: Entity class with non-empty ``_entity_info``.

        Returns:
            ``FacetVertex`` with ``node_type=\"Entity\"``.
        """
        snap = cls.facet_snapshot_for_class(target_cls)
        assert snap is not None
        return snap.to_facet_vertex()


# Backward-compatible module-level aliases for helper collectors.
EntityInfo = EntityIntentInspector.Snapshot.EntityInfo
EntityFieldInfo = EntityIntentInspector.Snapshot.EntityFieldInfo
EntityRelationInfo = EntityIntentInspector.Snapshot.EntityRelationInfo
EntityLifecycleInfo = EntityIntentInspector.Snapshot.EntityLifecycleInfo
