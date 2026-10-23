# packages/aoa-action-machine/src/aoa/action_machine/graph/validators/entity_field_validator.py
"""
EntityFieldValidator — refuse an entity-typed field that declares nothing.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A field whose resolved type is a structural entity is a relation by nature. Written
as a bare type, as a collection of an entity, as a bare ``X | None``, or as a state
entity, it is silently accepted today and becomes an ordinary column with no edge —
the graph then describes a model that does not exist.

A field whose resolved type is a dictionary is a reference by nature. Its bare type
and its optional form are the declaration, so they are accepted; a collection of
dictionary values, a relation container around one, and the embedded-value marker are
refused, because each states something the type does not.

This module refuses those forms before the graph is published, and names the legal
forms in the message: a relation container or ``NoRelation("reason")`` for a
structural entity, and the dictionary type itself for a reference.

═══════════════════════════════════════════════════════════════════════════════
RULES
═══════════════════════════════════════════════════════════════════════════════

- A Core, Assoc, Detail or Spec field MUST carry a relation container, or
  ``NoRelation("reason")``.
- A state-entity field has no form at all: a state is described by a
  ``Lifecycle[...]`` subclass, never by the entity type itself.
- A dictionary field MUST be the bare dictionary type, optionally ``| None``. A
  collection, a relation container, the marker, an empty catalogue and a dictionary
  without a graph node are refused.
- A lifecycle field, a schema type and every ordinary scalar pass untouched.
- A class excluded from the graph is not judged.

═══════════════════════════════════════════════════════════════════════════════
DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    @entity classes -> model_fields (annotations Pydantic resolved)
                          │
                          ├─ relation container?  -> accepted, target kind checked
                          ├─ NoRelation marker?   -> accepted on Core/Assoc/Detail/Spec
                          ├─ structural type?     -> EntityFieldDeclarationError
                          ├─ optional of one?     -> EntityFieldDeclarationError
                          ├─ collection of one?   -> EntityFieldDeclarationError
                          ├─ dictionary type?     -> accepted, catalogue and node checked
                          ├─ container of one?    -> EntityFieldDeclarationError
                          └─ collection/union of  -> EntityFieldDeclarationError
"""

from __future__ import annotations

import types
import typing
from collections.abc import Mapping
from typing import Annotated, Any, get_args, get_origin

from pydantic.fields import FieldInfo

from aoa.action_machine.domain.assoc_entity import BaseAssocEntity
from aoa.action_machine.domain.core_entity import BaseCoreEntity
from aoa.action_machine.domain.detail_entity import BaseDetailEntity
from aoa.action_machine.domain.entity import BaseEntity
from aoa.action_machine.domain.enum_entity import BaseEnumEntity
from aoa.action_machine.domain.exceptions import EntityFieldDeclarationError
from aoa.action_machine.domain.relation_markers import Inverse, NoGraphEdge, NoInverse, NoRelation
from aoa.action_machine.domain.spec_entity import BaseSpecEntity
from aoa.action_machine.domain.specialization_containers import Generalization
from aoa.action_machine.domain.state_entity import BaseStateEntity
from aoa.action_machine.graph.core.exclude_graph_model import excluded_from_graph_model
from aoa.action_machine.graph.validators.entity_specialization_validator import declared_entity_classes
from aoa.action_machine.intents.entity.entity_intent import entity_info_is_set
from aoa.action_machine.intents.entity.entity_relation_intent_resolver import is_relation_container
from aoa.action_machine.intents.entity.entity_specialization_intent_resolver import (
    is_specialization_field,
)

__all__ = ["validate_entity_fields"]

_ENTITY_BASES: tuple[tuple[type[Any], str], ...] = (
    (BaseCoreEntity, "Core"),
    (BaseAssocEntity, "Assoc"),
    (BaseDetailEntity, "Detail"),
    (BaseSpecEntity, "Spec"),
)
_RELATION_MARKERS: tuple[type[Any], ...] = (Inverse, NoInverse, NoGraphEdge)


def _kind_of(annotation: Any) -> str | None:
    """Return the entity kind ``annotation`` names, or ``None`` when it names none."""
    if not isinstance(annotation, type):
        return None
    for base, kind in _ENTITY_BASES:
        if issubclass(annotation, base):
            return kind
    if issubclass(annotation, BaseEnumEntity):
        return "Enum"
    if issubclass(annotation, BaseStateEntity):
        return "State"
    return None


def _describe(annotation: Any) -> str:
    """Return a short readable name for an annotation, keeping a container's arguments."""
    name = getattr(annotation, "__name__", None)
    if isinstance(name, str) and get_origin(annotation) is None and not get_args(annotation):
        return name
    return str(annotation)


def _strip_optional(annotation: Any) -> tuple[Any, bool]:
    """Return the annotation without ``None`` and whether ``None`` was allowed."""
    origin = get_origin(annotation)
    if origin is not types.UnionType and origin is not typing.Union:
        return annotation, False
    args = [arg for arg in get_args(annotation) if arg is not type(None)]
    if len(args) != 1:
        return annotation, any(arg is type(None) for arg in get_args(annotation))
    return args[0], True


def _entity_inside(annotation: Any) -> Any | None:
    """Return the entity contained anywhere in ``annotation``, or ``None``."""
    if get_origin(annotation) is Annotated:
        return _entity_inside(get_args(annotation)[0])
    if _kind_of(annotation) is not None:
        return annotation
    metadata = getattr(annotation, "__pydantic_generic_metadata__", None)
    if isinstance(metadata, dict):
        for arg in metadata.get("args") or ():
            found = _entity_inside(arg)
            if found is not None:
                return found
    origin = get_origin(annotation)
    if origin is None:
        return None
    for arg in get_args(annotation):
        if arg is type(None) or arg is Ellipsis:
            continue
        found = _entity_inside(arg)
        if found is not None:
            return found
    return None


def _collect_entities(annotation: Any, found: list[Any]) -> None:
    """Append every entity named anywhere in ``annotation`` to ``found``, in order, once each."""
    if get_origin(annotation) is Annotated:
        _collect_entities(get_args(annotation)[0], found)
        return
    if _kind_of(annotation) is not None:
        if annotation not in found:
            found.append(annotation)
        return
    metadata = getattr(annotation, "__pydantic_generic_metadata__", None)
    if isinstance(metadata, dict):
        for arg in metadata.get("args") or ():
            _collect_entities(arg, found)
    for arg in get_args(annotation):
        if arg is type(None) or arg is Ellipsis:
            continue
        _collect_entities(arg, found)


def _entities_inside(annotation: Any) -> list[Any]:
    """Return every distinct entity ``annotation`` names, in declaration order."""
    found: list[Any] = []
    _collect_entities(annotation, found)
    return found


def _shape_of(annotation: Any) -> str:
    """Return ``union``, ``mapping`` or ``collection`` for an annotation that holds an entity."""
    origin = get_origin(annotation)
    if origin is types.UnionType or origin is typing.Union:
        return "union"
    if isinstance(origin, type) and issubclass(origin, Mapping):
        return "mapping"
    return "collection"


def _state_refusal(target: Any) -> str:
    """Return the message for a field whose type is a state entity."""
    return (
        f"the field's type is a state entity ({_describe(target)}); a state is neither a relation "
        f"nor a plain field. Declare a Lifecycle[...] subclass on the field instead."
    )


def _structural_refusal(target: Any, annotation: Any) -> str:
    """Return the message for a bare or optional structural-entity field."""
    name = _describe(target)
    optional = " | None" in str(annotation)
    shape = f"{name} | None" if optional else name
    return (
        f"the field's type is an entity ({shape}), so the field cannot be a scalar. Declare it as a "
        f"relation (Annotated[AssociationOne[{name}], Inverse(...)]) or as an embedded value "
        f'(Annotated[{shape}, NoRelation("reason")]).'
    )


def _collection_refusal(target: Any, annotation: Any) -> str:
    """Return the message for a collection of a structural entity."""
    name = _describe(target)
    return (
        f"the field's type is a collection of an entity ({_describe(annotation)}); a collection is not "
        f"a relation. Declare the many relation "
        f"(Annotated[AssociationMany[{name}], Inverse(...)]) or mark the field as an embedded value "
        f'(Annotated[{name}, NoRelation("reason")]).'
    )


def _union_refusal(entities: list[Any], annotation: Any) -> str:
    """Return the message for a union that names two or more entities."""
    names = " and ".join(_describe(entity) for entity in entities)
    return (
        f"the field's type is a union of entities ({_describe(annotation)}), so the field names "
        f"{names} at once. Declare one field per entity, each with its own relation or "
        f"embedded-value form."
    )


def _heterogeneous_collection_refusal(entities: list[Any], annotation: Any) -> str:
    """Return the message for a collection that names two or more entities."""
    names = ", ".join(_describe(entity) for entity in entities)
    return (
        f"the field's type is a collection of {len(entities)} entities ({_describe(annotation)}); "
        f"a collection is not a relation. Declare one field per entity ({names}), each with its "
        f"own relation or embedded-value form."
    )


def _mapping_refusal(annotation: Any) -> str:
    """Return the message for a mapping whose value is an entity."""
    return (
        f"the field's type is a mapping to an entity ({_describe(annotation)}), and a mapping is "
        f"not a relation. Declare the relation on the owning entity, or model the mapping as its "
        f"own entity."
    )


def _dictionary_collection_refusal(target: Any, annotation: Any) -> str:
    """Return the message for a collection of dictionary values."""
    name = _describe(target)
    return (
        f"a collection of dictionary values has no declared form ({_describe(annotation)}); a "
        f"dictionary reference is one value. Write {name}, or {name} | None for an optional one."
    )


def _dictionary_union_refusal(target: Any, annotation: Any) -> str:
    """Return the message for a union that names more than one dictionary."""
    name = _describe(target)
    return (
        f"the field's type names more than one dictionary ({_describe(annotation)}), and a "
        f"dictionary reference is one value. Write {name}, or {name} | None for an optional one."
    )


def _dictionary_container_refusal(target: Any) -> str:
    """Return the message for a relation container around a dictionary."""
    name = _describe(target)
    return (
        f"the field's type is a relation container around a dictionary ({name}); a dictionary value "
        f"is a shared reference, not an association target. Write {name} on the field instead."
    )


def _dictionary_marker_refusal(target: Any) -> str:
    """Return the message for the embedded-value marker on a dictionary."""
    name = _describe(target)
    return (
        f"NoRelation marks an embedded structural entity, and this field's type is a dictionary "
        f"({name}): the bare dictionary type already declares the reference. Remove the marker and "
        f"keep {name} on the field."
    )


def _empty_catalogue_refusal(dictionary: Any) -> str:
    """Return the message for a field typed by a dictionary with no values."""
    return f"{_describe(dictionary)} declares no values; type the field with a concrete dictionary."


def _dictionary_outside_graph_refusal(dictionary: Any) -> str:
    """Return the message for a reference to a dictionary that has no graph node."""
    return (
        f"{_describe(dictionary)} has no node in the graph: it is not a declared @entity class, or "
        f"it is marked exclude_graph_model, so the reference could not be drawn. Keep the dictionary "
        f"in the graph."
    )


def _refuse(entity_cls: type[BaseEntity], field_name: str, details: str) -> None:
    """Raise the declaration error for one field."""
    raise EntityFieldDeclarationError(entity_cls.__name__, field_name, details)


def _is_relation_field(annotation: Any) -> bool:
    """True when the annotation is any of the eight relation containers."""
    if is_relation_container(annotation) or is_specialization_field(annotation):
        return True
    return isinstance(annotation, type) and issubclass(annotation, Generalization)


def _require_relation_metadata(
    entity_cls: type[BaseEntity], field_name: str, field_info: FieldInfo, annotation: Any
) -> None:
    """Enforce the description and default contract of a relation field."""
    description = field_info.description
    if not isinstance(description, str) or not description.strip():
        _refuse(
            entity_cls,
            field_name,
            'a relation field needs a non-blank description; write it as Field(description="...").',
        )
    if field_info.default_factory is not None:
        _refuse(
            entity_cls,
            field_name,
            "a relation field cannot use default_factory; supply the value, or declare "
            "default=None on a nullable relation.",
        )
    if field_info.is_required():
        return
    inner, allows_none = _strip_optional(annotation)
    default = field_info.default
    if default is None:
        if allows_none:
            return
        _refuse(
            entity_cls,
            field_name,
            f"default=None needs a nullable annotation; write "
            f"Annotated[{_describe(inner)} | None, ...] = Field(default=None, description=...).",
        )
    _refuse(
        entity_cls,
        field_name,
        "a relation field takes no default other than an explicit None on a nullable relation; "
        "a description belongs to Field(description=...), and the value is supplied by the caller.",
    )


def _check_relation(entity_cls: type[BaseEntity], field_name: str, field_info: FieldInfo, annotation: Any) -> bool:
    """Check a relation field and return whether the field was one."""
    if not _is_relation_field(annotation):
        return False
    if any(isinstance(marker, NoRelation) for marker in field_info.metadata):
        _refuse(
            entity_cls,
            field_name,
            "NoRelation and a relation container cannot be combined; keep the container, or state why "
            "no relation exists.",
        )
    target = _entity_inside(annotation)
    if target is not None and _kind_of(target) == "State":
        _refuse(entity_cls, field_name, _state_refusal(target))
    if target is not None and _kind_of(target) == "Enum":
        _refuse(entity_cls, field_name, _dictionary_container_refusal(target))
    _require_relation_metadata(entity_cls, field_name, field_info, annotation)
    return True


def _check_marker(entity_cls: type[BaseEntity], field_name: str, field_info: FieldInfo, annotation: Any) -> bool:
    """Check an embedded-value marker and return whether the field carried one."""
    marker = next((item for item in field_info.metadata if isinstance(item, NoRelation)), None)
    if marker is None:
        return False
    if any(isinstance(item, _RELATION_MARKERS) for item in field_info.metadata):
        _refuse(
            entity_cls,
            field_name,
            "NoRelation and a relation marker cannot be combined; the field either has a relation or it does not.",
        )
    inner, _optional = _strip_optional(annotation)
    kind = _kind_of(inner)
    if kind == "State":
        _refuse(entity_cls, field_name, _state_refusal(inner))
    if kind == "Enum":
        _refuse(entity_cls, field_name, _dictionary_marker_refusal(inner))
    if kind is None:
        _refuse(
            entity_cls,
            field_name,
            f"NoRelation marks an embedded value, so it applies only to a Core, Assoc, Detail or Spec "
            f"entity; this field's type is {_describe(annotation)}.",
        )
    return True


def _check_shape(entity_cls: type[BaseEntity], field_name: str, annotation: Any) -> None:
    """Refuse a union, a mapping or a heterogeneous collection; return for every other shape."""
    entities = _entities_inside(annotation)
    shape = _shape_of(annotation)
    if shape == "union" and len(entities) > 1:
        _refuse(entity_cls, field_name, _union_refusal(entities, annotation))
    if shape == "mapping":
        _refuse(entity_cls, field_name, _mapping_refusal(annotation))
    if len(entities) > 1:
        _refuse(entity_cls, field_name, _heterogeneous_collection_refusal(entities, annotation))


def _require_dictionary_node(entity_cls: type[BaseEntity], field_name: str, dictionary: Any) -> None:
    """Refuse a reference to a dictionary with no values or with no graph node."""
    if not getattr(dictionary, "members", ()):
        _refuse(entity_cls, field_name, _empty_catalogue_refusal(dictionary))
    if not entity_info_is_set(dictionary) or excluded_from_graph_model(dictionary):
        _refuse(entity_cls, field_name, _dictionary_outside_graph_refusal(dictionary))


def _check_field(entity_cls: type[BaseEntity], field_name: str, field_info: FieldInfo) -> None:
    """Apply the declaration rule to one field."""
    annotation = field_info.annotation
    if _check_relation(entity_cls, field_name, field_info, annotation):
        return
    if _check_marker(entity_cls, field_name, field_info, annotation):
        return
    inner, allowed_none = _strip_optional(annotation)
    inner_kind = _kind_of(inner)
    if inner_kind == "Enum":
        _require_dictionary_node(entity_cls, field_name, inner)
        return
    if inner_kind == "State":
        _refuse(entity_cls, field_name, _state_refusal(inner))
    if inner_kind is not None:
        _refuse(entity_cls, field_name, _structural_refusal(inner, annotation))
    target = _entity_inside(annotation)
    if target is None:
        return
    target_kind = _kind_of(target)
    if target_kind == "State":
        _refuse(entity_cls, field_name, _state_refusal(target))
    if target_kind == "Enum":
        if get_origin(annotation) in (types.UnionType, typing.Union):
            _refuse(entity_cls, field_name, _dictionary_union_refusal(target, annotation))
        _refuse(entity_cls, field_name, _dictionary_collection_refusal(target, annotation))
    _check_shape(entity_cls, field_name, annotation)
    if allowed_none:
        _refuse(entity_cls, field_name, _structural_refusal(target, annotation))
    _refuse(entity_cls, field_name, _collection_refusal(target, annotation))


def validate_entity_fields(entities: list[type[BaseEntity]] | None = None) -> None:
    """
    Refuse every entity field that names an entity without declaring its form.

    Args:
        entities: classes to judge; when ``None``, every loaded ``@entity`` class is used.

    Raises:
        EntityFieldDeclarationError: a field is a bare entity, a collection of one, a bare
            optional of one, a state entity, a misused embedded-value marker, or a dictionary
            reference declared as a collection, a container, a marker, an empty catalogue or a
            dictionary without a graph node.
    """
    for entity_cls in declared_entity_classes() if entities is None else entities:
        for field_name, field_info in entity_cls.model_fields.items():
            _check_field(entity_cls, field_name, field_info)
