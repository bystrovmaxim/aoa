# src/action_machine/intents/entity/entity_relation_intent_resolver.py
"""EntityRelationIntentResolver — freeze one declared entity→entity relation from ``model_fields``."""

from __future__ import annotations

import inspect
import types
import typing
from dataclasses import dataclass
from typing import Annotated, Any, get_args, get_origin

from pydantic.fields import FieldInfo

from action_machine.domain.relation_containers import BaseRelationMany, BaseRelationOne
from action_machine.domain.relation_markers import Inverse, NoGraphEdge, NoInverse, Rel


@dataclass(frozen=True)
class EntityRelationIntentResolver:
    """
    One ``BaseRelationOne`` / ``BaseRelationMany`` field on an entity host class.

    ``relation_type`` is the declarative arc (``composition`` / ``aggregation`` / ``association``).
    ``cardinality`` is ``one`` or ``many``.
    """

    field_name: str
    target_entity: type[Any]
    relation_type: str
    cardinality: str
    container_class: type[Any]
    description: str = ""
    has_inverse: bool = False
    inverse_entity: type[Any] | None = None
    inverse_field: str | None = None
    deprecated: bool = False
    omit_graph_edge: bool = False


def _union_contains_relation_container(annotation: Any) -> bool:
    return any(
        arg is not types.NoneType and _is_relation_container(arg)
        for arg in get_args(annotation)
    )


def _origin_is_relation_container(origin: Any) -> bool:
    return origin is not None and inspect.isclass(origin) and issubclass(
        origin,
        (BaseRelationOne, BaseRelationMany),
    )


def _is_relation_container(annotation: Any) -> bool:
    """
    True if ``annotation`` denotes ``BaseRelationOne`` / ``BaseRelationMany``
    (including inside ``Optional`` / ``Annotated``).

    Duplicated from :mod:`action_machine.legacy.entity_intent_inspector`; keep aligned manually.
    """
    if get_origin(annotation) is Annotated:
        return _is_relation_container(get_args(annotation)[0])

    origin_bt = get_origin(annotation)
    if origin_bt is types.UnionType or origin_bt is typing.Union:
        return _union_contains_relation_container(annotation)

    if _origin_is_relation_container(origin_bt):
        return True

    return isinstance(annotation, type) and issubclass(annotation, (BaseRelationOne, BaseRelationMany))


def _strip_annotated_metadata(annotation: Any) -> tuple[Any, tuple[Any, ...]]:
    if get_origin(annotation) is Annotated:
        args = get_args(annotation)
        return args[0], tuple(args[1:])
    return annotation, ()


def _first_non_optional_member(typ: Any) -> Any:
    origin_bt0 = get_origin(typ)
    if origin_bt0 is not types.UnionType and origin_bt0 is not typing.Union:
        return typ
    for arg in get_args(typ):
        if arg is not types.NoneType:
            return arg
    return typ


def _relation_container_pair(base_type: Any) -> tuple[type[Any], type[Any]] | None:
    """Return ``(container_class, target_entity)`` or ``None`` when not a relation field."""
    origin_bt = get_origin(base_type)

    container_class = None
    if origin_bt is not None and inspect.isclass(origin_bt) and issubclass(
        origin_bt,
        (BaseRelationOne, BaseRelationMany),
    ):
        container_class = origin_bt
    elif isinstance(base_type, type) and issubclass(base_type, (BaseRelationOne, BaseRelationMany)):
        container_class = base_type

    if container_class is None:
        return None

    container_args = get_args(base_type)
    target_entity = None
    if container_args and isinstance(container_args[0], type):
        target_entity = container_args[0]

    return (container_class, target_entity) if target_entity is not None else None


def _markers_from_annotation_metadata(metadata: tuple[Any, ...]) -> tuple[bool, type[Any] | None, str | None]:
    """``has_inverse``, ``inverse_entity``, ``inverse_field`` from ``Inverse`` / ``NoInverse``."""
    has_inverse = False
    inverse_entity: type[Any] | None = None
    inverse_field: str | None = None
    for item in metadata:
        if isinstance(item, Inverse):
            has_inverse = True
            inverse_entity = item.target_entity
            inverse_field = item.field_name
            break
        if isinstance(item, NoInverse):
            break
    return has_inverse, inverse_entity, inverse_field


def _field_description_hint(field_info: FieldInfo) -> str:
    default_val = field_info.default
    if isinstance(default_val, Rel):
        return default_val.description
    if field_info.description:
        return field_info.description
    return ""


def _relation_from_field(
    field_name: str,
    annotation: Any,
    field_info: FieldInfo,
) -> EntityRelationIntentResolver | None:
    """
    Parse ``Annotated[..., Inverse | NoInverse, NoGraphEdge?, ...]`` plus container type.

    Duplicate of legacy ``_extract_relation_info``.
    """
    base_type, annotated_metadata = _strip_annotated_metadata(annotation)
    container_pair = _relation_container_pair(_first_non_optional_member(base_type))
    if container_pair is None:
        return None
    container_class, target_entity = container_pair

    relation_type = container_class.relation_type.value
    cardinality = "one" if issubclass(container_class, BaseRelationOne) else "many"

    has_inverse, inverse_entity, inverse_field = _markers_from_annotation_metadata(annotated_metadata)
    omit_graph_edge = any(isinstance(item, NoGraphEdge) for item in annotated_metadata)

    return EntityRelationIntentResolver(
        field_name=field_name,
        target_entity=target_entity,
        relation_type=relation_type,
        cardinality=cardinality,
        container_class=container_class,
        description=_field_description_hint(field_info),
        has_inverse=has_inverse,
        inverse_entity=inverse_entity,
        inverse_field=inverse_field,
        deprecated=bool(getattr(field_info, "deprecated", False)),
        omit_graph_edge=omit_graph_edge,
    )


def gather_entity_relation_intent_resolvers(host_cls: type) -> list[EntityRelationIntentResolver]:
    """
    All relation-container fields on ``host_cls`` (same contract as legacy ``collect_entity_relations``).
    """
    model_fields = getattr(host_cls, "model_fields", None)
    if not model_fields:
        return []

    try:
        from typing_extensions import get_type_hints  # pylint: disable=import-outside-toplevel

        hints = get_type_hints(host_cls, include_extras=True)
    except Exception:
        hints = {}

    out: list[EntityRelationIntentResolver] = []
    for field_name, field_info in model_fields.items():
        annotation = hints.get(field_name, field_info.annotation)
        if not _is_relation_container(annotation):
            continue
        resolved = _relation_from_field(field_name, annotation, field_info)
        if resolved is not None:
            out.append(resolved)
    return out
