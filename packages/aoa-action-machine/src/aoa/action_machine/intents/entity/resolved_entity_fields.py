# packages/aoa-action-machine/src/aoa/action_machine/intents/entity/resolved_entity_fields.py
"""
ResolvedEntityField — the build-local normalized view of one entity field.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Pydantic merges a field's annotation, ``Annotated`` markers and ``Field(...)``
settings into one ``FieldInfo``. Every consumer — the relation resolver, the
completeness validator and the inverse validator — must read the same resolved view
instead of each re-parsing the original annotation. This module is that single view.

A field is normalized once from ``FieldInfo.annotation`` and ``FieldInfo.metadata``.
The original module globals are **never** re-evaluated with ``get_type_hints``; a
successful ``model_rebuild`` already resolved the annotation, and the markers live in
``FieldInfo.metadata`` where Pydantic put them.

═══════════════════════════════════════════════════════════════════════════════
SCOPE (IN / OUT)
═══════════════════════════════════════════════════════════════════════════════

**In scope**
    Normalizing one field into a frozen descriptor: host, declaring owner, annotation,
    metadata, description/default contract, relation kind/cardinality, resolved target
    classes and direction markers.

**Out of scope**
    Proving the inverse field exists or the pair is compatible — the validators do that.
    Loading rows or constructing values.
    A global registry — this is a per-assembly, build-local view.

═══════════════════════════════════════════════════════════════════════════════
RATIONALE
═══════════════════════════════════════════════════════════════════════════════

Reading markers from the recovered annotation loses them when the annotation is only
resolved after an explicit ``model_rebuild``; reading them from ``FieldInfo.metadata``
keeps every marker Pydantic preserved. Selecting the first member of an ambiguous union
silently misdescribes a field, so a union with more than one relation-bearing member is
refused instead. Target classes are compared by identity, never by short name.

═══════════════════════════════════════════════════════════════════════════════
LIFECYCLE (IMPORT VS BUILD VS RUNTIME)
═══════════════════════════════════════════════════════════════════════════════

- **Build**: ``resolve_entity_fields`` walks a host's ``model_fields`` once per assembly.
- **Runtime**: descriptors are read-only; instance values are never touched here.
"""

from __future__ import annotations

import inspect
import types
import typing
from dataclasses import dataclass, replace
from typing import Any, get_args, get_origin

from pydantic.fields import FieldInfo

from aoa.action_machine.domain.exceptions import EntityFieldDeclarationError
from aoa.action_machine.domain.relation_containers import BaseRelationMany, BaseRelationOne
from aoa.action_machine.domain.relation_markers import Inverse, NoGraphEdge, NoInverse, NoRelation
from aoa.action_machine.domain.specialization_containers import Classifier, Generalization, Specialization

__all__ = [
    "ResolvedEntityField",
    "declaring_owner_of",
    "is_generalization_container",
    "is_relation_container",
    "is_specialization_container",
    "resolve_entity_field",
    "resolve_entity_fields",
]

_DIRECTION_MARKERS = (Inverse, NoInverse)


@dataclass(frozen=True)
class ResolvedEntityField:
    """
    One normalized entity field.

    AI-CORE-BEGIN
        ROLE: Build-local normalized view of a single declared field.
        CONTRACT: Every field of a loaded host resolves to one descriptor; markers come
            from ``FieldInfo.metadata`` and targets from the resolved annotation by class
            identity.
        INVARIANTS: ``direction_marker_count`` is the count of Inverse/NoInverse markers;
            ``targets`` holds only real classes; the descriptor is frozen and never mutated.
        AI-CORE-END
    """

    effective_host: type[Any]
    declaring_owner: type[Any]
    field_name: str
    annotation: Any
    metadata: tuple[Any, ...]
    description: str
    deprecated: bool
    default: Any
    default_factory: Any
    required: bool
    nullable: bool

    is_relation: bool
    is_specialization: bool
    is_generalization: bool
    container: type[Any] | None
    relation_kind: str | None
    cardinality: str | None
    targets: tuple[type[Any], ...]
    dictionary: type[Any] | None

    has_inverse: bool
    inverse_entity: type[Any] | None
    inverse_field: str | None
    omit_graph_edge: bool
    has_no_relation: bool
    classifier: Classifier | None
    direction_markers: tuple[Any, ...]

    @property
    def direction_marker_count(self) -> int:
        """Number of Inverse/NoInverse markers the field carries."""
        return len(self.direction_markers)


def _container_origin_and_args(annotation: Any) -> tuple[Any, tuple[Any, ...]]:
    """Return ``(origin, args)`` for a subscripted container, whatever form it took."""
    origin = get_origin(annotation)
    if origin is not None:
        return origin, get_args(annotation)
    # Pydantic materializes BaseModel generics (Specialization / Generalization) into real
    # classes; their arguments survive in __pydantic_generic_metadata__.
    metadata = getattr(annotation, "__pydantic_generic_metadata__", None)
    if isinstance(metadata, dict) and metadata.get("origin") is not None:
        return metadata["origin"], tuple(metadata.get("args") or ())
    return None, ()


def _is_container_subclass(origin: Any, bases: tuple[type[Any], ...]) -> bool:
    """True when ``origin`` is a class that inherits any of ``bases``."""
    return origin is not None and inspect.isclass(origin) and issubclass(origin, bases)


def is_relation_container(annotation: Any) -> bool:
    """
    True when ``annotation`` denotes ``BaseRelationOne`` / ``BaseRelationMany``.

    Handles the bare subscripted container, its optional form, and a class that is itself
    a relation container. ``field_info.annotation`` is already ``Annotated``-stripped, so
    an outer ``Annotated`` is handled defensively but is not the common path.
    """
    origin, _ = _container_origin_and_args(annotation)
    if _is_container_subclass(origin, (BaseRelationOne, BaseRelationMany)):
        return True
    if isinstance(annotation, type) and issubclass(annotation, (BaseRelationOne, BaseRelationMany)):
        return True
    # Optional / union wrapping one relation container.
    if get_origin(annotation) in (types.UnionType, typing.Union):
        return any(arg is not types.NoneType and is_relation_container(arg) for arg in get_args(annotation))
    return False


def is_specialization_container(annotation: Any) -> bool:
    """True when ``annotation`` is a subscripted ``Specialization`` container."""
    origin, args = _container_origin_and_args(annotation)
    return _is_container_subclass(origin, (Specialization,)) and bool(args)


def is_generalization_container(annotation: Any) -> bool:
    """True when ``annotation`` is a subscripted ``Generalization`` container."""
    origin, args = _container_origin_and_args(annotation)
    return _is_container_subclass(origin, (Generalization,)) and bool(args)


def _strip_optional(annotation: Any) -> tuple[Any, bool, int]:
    """Return ``(inner, nullable, member_count)``.

    ``member_count`` is the number of non-None members; it is greater than one for an
    ambiguous union such as ``AssociationOne[A] | AssociationOne[B]``.
    """
    origin = get_origin(annotation)
    if origin not in (types.UnionType, typing.Union):
        return annotation, False, 1
    args = get_args(annotation)
    non_none = [arg for arg in args if arg is not types.NoneType]
    nullable = len(non_none) != len(args)
    if len(non_none) == 1:
        return non_none[0], nullable, 1
    return annotation, nullable, len(non_none)


def _direction_markers(metadata: tuple[Any, ...]) -> tuple[Any, ...]:
    """Return the Inverse/NoInverse markers in declaration order."""
    return tuple(item for item in metadata if isinstance(item, _DIRECTION_MARKERS))


def _inverse_parts(
    metadata: tuple[Any, ...],
) -> tuple[bool, type[Any] | None, str | None]:
    """Return ``(has_inverse, inverse_entity, inverse_field)`` from the markers."""
    for item in metadata:
        if isinstance(item, Inverse):
            return True, item.target_entity, item.field_name
        if isinstance(item, NoInverse):
            break
    return False, None, None


def _relation_target(annotation: Any) -> type[Any] | None:
    """Return the single resolved target of a relation container, or ``None``."""
    _, args = _container_origin_and_args(annotation)
    if args and isinstance(args[0], type):
        return args[0]
    return None


def _relation_kind_and_cardinality(origin: Any) -> tuple[str, str]:
    """Return ``(kind, cardinality)`` for a relation container origin."""
    kind = origin.relation_type.value
    cardinality = "one" if issubclass(origin, BaseRelationOne) else "many"
    return kind, cardinality


def _union_members(annotation: Any) -> tuple[type[Any], ...]:
    """Flatten a union into its non-None members."""
    origin = get_origin(annotation)
    if origin in (types.UnionType, typing.Union):
        return tuple(arg for arg in get_args(annotation) if arg is not types.NoneType)
    return (annotation,)


def _specialization_parts(annotation: Any) -> tuple[tuple[type[Any], ...], type[Any] | None]:
    """Return ``(alternatives, dictionary)`` for a ``Specialization`` container."""
    _, args = _container_origin_and_args(annotation)
    alternatives: tuple[type[Any], ...] = ()
    dictionary: type[Any] | None = None
    if args:
        alternatives = tuple(arg for arg in _union_members(args[0]) if isinstance(arg, type))
    if len(args) == 2 and isinstance(args[1], type):
        dictionary = args[1]
    return alternatives, dictionary


def _generalization_target(annotation: Any) -> type[Any] | None:
    """Return the head of a ``Generalization`` container, or ``None``."""
    _, args = _container_origin_and_args(annotation)
    if not args:
        return None
    members = _union_members(args[0])
    return members[0] if members and isinstance(members[0], type) else None


def _infer_field_only_inverse(field: ResolvedEntityField) -> ResolvedEntityField:
    """Infer the inverse target of a field-only ``Inverse(field_name=...)`` from the container."""
    if field.has_inverse and field.inverse_entity is None and len(field.targets) == 1:
        return replace(field, inverse_entity=field.targets[0])
    return field


def _refuse_ambiguous(host: type[Any], field_name: str, annotation: Any, member_count: int) -> None:
    """Raise the declaration error for a relation field that names more than one shape."""
    raise EntityFieldDeclarationError(
        host.__name__,
        field_name,
        f"the field's type is an ambiguous union ({annotation}); a relation field names exactly "
        f"one container, and {member_count} non-None members were found. Split them into "
        f"separate fields.",
    )


def resolve_entity_field(
    host_cls: type[Any],
    field_name: str,
    field_info: FieldInfo,
) -> ResolvedEntityField:
    """
    Normalize one field of ``host_cls`` into a :class:`ResolvedEntityField`.

    Args:
        host_cls: The effective host whose ``model_fields`` the field was read from.
        field_name: The field's name.
        field_info: The completed ``FieldInfo`` Pydantic built for the field.

    Raises:
        EntityFieldDeclarationError: The field is a relation field whose annotation is an
            ambiguous union (more than one non-None relation-bearing member).
    """
    annotation = field_info.annotation
    metadata = tuple(field_info.metadata)
    inner, nullable, member_count = _strip_optional(annotation)

    inverse_markers = _direction_markers(metadata)
    has_inverse, inverse_entity, inverse_field = _inverse_parts(metadata)
    classifier = next((item for item in metadata if isinstance(item, Classifier)), None)

    common = {
        "effective_host": host_cls,
        "declaring_owner": declaring_owner_of(host_cls, field_name),
        "field_name": field_name,
        "annotation": annotation,
        "metadata": metadata,
        "description": field_info.description or "",
        "deprecated": bool(getattr(field_info, "deprecated", False)),
        "default": field_info.default,
        "default_factory": field_info.default_factory,
        "required": field_info.is_required(),
        "nullable": nullable,
        "has_inverse": has_inverse,
        "inverse_entity": inverse_entity,
        "inverse_field": inverse_field,
        "omit_graph_edge": any(isinstance(item, NoGraphEdge) for item in metadata),
        "has_no_relation": any(isinstance(item, NoRelation) for item in metadata),
        "classifier": classifier,
        "direction_markers": inverse_markers,
    }

    if is_relation_container(annotation):
        if member_count > 1:
            _refuse_ambiguous(host_cls, field_name, annotation, member_count)
        origin, _ = _container_origin_and_args(inner)
        container_cls: type[Any] | None = None
        if _is_container_subclass(origin, (BaseRelationOne, BaseRelationMany)):
            container_cls = origin
        elif isinstance(inner, type) and issubclass(inner, (BaseRelationOne, BaseRelationMany)):
            container_cls = inner
        if container_cls is None:
            # Relation-shaped but no resolvable container (an unresolved forward reference);
            # the completeness validator refuses the unresolved target, not this resolver.
            return ResolvedEntityField(
                is_relation=True,
                is_specialization=False,
                is_generalization=False,
                container=None,
                relation_kind=None,
                cardinality=None,
                targets=(),
                dictionary=None,
                **common,
            )
        kind, cardinality = _relation_kind_and_cardinality(container_cls)
        target = _relation_target(inner)
        return _infer_field_only_inverse(
            ResolvedEntityField(
                is_relation=True,
                is_specialization=False,
                is_generalization=False,
                container=container_cls,
                relation_kind=kind,
                cardinality=cardinality,
                targets=(target,) if target is not None else (),
                dictionary=None,
                **common,
            )
        )

    if is_specialization_container(annotation):
        alternatives, dictionary = _specialization_parts(inner)
        return ResolvedEntityField(
            is_relation=False,
            is_specialization=True,
            is_generalization=False,
            container=Specialization,
            relation_kind="specialization",
            cardinality=None,
            targets=alternatives,
            dictionary=dictionary,
            **common,
        )

    if is_generalization_container(annotation):
        head = _generalization_target(inner)
        return _infer_field_only_inverse(
            ResolvedEntityField(
                is_relation=False,
                is_specialization=False,
                is_generalization=True,
                container=Generalization,
                relation_kind="generalization",
                cardinality="one",
                targets=(head,) if head is not None else (),
                dictionary=None,
                **common,
            )
        )

    return ResolvedEntityField(
        is_relation=False,
        is_specialization=False,
        is_generalization=False,
        container=None,
        relation_kind=None,
        cardinality=None,
        targets=(),
        dictionary=None,
        **common,
    )


def resolve_entity_fields(host_cls: type) -> list[ResolvedEntityField]:
    """Return a normalized descriptor for every field of ``host_cls``, in field order."""
    model_fields = getattr(host_cls, "model_fields", None)
    if not model_fields:
        return []
    return [resolve_entity_field(host_cls, name, info) for name, info in model_fields.items()]


def _same_field_signature(left: FieldInfo, right: FieldInfo) -> bool:
    """True when two field records describe the same relationship signature."""
    return left.annotation == right.annotation and tuple(left.metadata) == tuple(right.metadata)


def declaring_owner_of(host_cls: type, field_name: str) -> type:
    """
    Return the class that introduced ``field_name`` as it is seen on ``host_cls``.

    An unchanged inherited field keeps the base class as its declaring owner; an override
    or a generic substitution that changed the resolved annotation makes ``host_cls`` (or
    the overriding subclass) the owner. Compared by the resolved annotation and metadata,
    never by a short name.
    """
    model_fields = getattr(host_cls, "model_fields", None)
    if not model_fields or field_name not in model_fields:
        return host_cls
    own = model_fields[field_name]
    for base in host_cls.__mro__[1:]:
        base_fields = getattr(base, "model_fields", None)
        if not base_fields or field_name not in base_fields:
            continue
        if _same_field_signature(own, base_fields[field_name]):
            return declaring_owner_of(base, field_name)
        return host_cls
    return host_cls
