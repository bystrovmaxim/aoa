# packages/aoa-action-machine/src/aoa/action_machine/graph/validators/entity_field_validator.py
"""
EntityFieldValidator — refuse a structural-entity field that declares nothing.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A field whose resolved type is a structural entity is a relation by nature. Written
as a bare type, as a collection of an entity, as a bare ``X | None``, or as a state
entity, it is silently accepted today and becomes an ordinary column with no edge —
the graph then describes a model that does not exist.

This module refuses those forms before the graph is published, and names the legal
forms in the message: a relation container, or ``NoRelation("reason")`` for a field
that deliberately embeds the entity as a value.

═══════════════════════════════════════════════════════════════════════════════
RULES
═══════════════════════════════════════════════════════════════════════════════

- A Core, Assoc, Detail or Spec field MUST carry a relation container, or
  ``NoRelation("reason")``.
- A state-entity field has no form at all: a state is described by a
  ``Lifecycle[...]`` subclass, never by the entity type itself.
- A dictionary reference, a lifecycle field, a schema type and every ordinary
  scalar are outside the rule and pass untouched.
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
                          └─ collection of one?   -> EntityFieldDeclarationError
"""

from __future__ import annotations

import types
import typing
from typing import Annotated, Any, get_args, get_origin

from pydantic.fields import FieldInfo

from aoa.action_machine.domain.assoc_entity import BaseAssocEntity
from aoa.action_machine.domain.core_entity import BaseCoreEntity
from aoa.action_machine.domain.detail_entity import BaseDetailEntity
from aoa.action_machine.domain.entity import BaseEntity
from aoa.action_machine.domain.exceptions import EntityFieldDeclarationError
from aoa.action_machine.domain.relation_markers import Inverse, NoGraphEdge, NoInverse, NoRelation
from aoa.action_machine.domain.spec_entity import BaseSpecEntity
from aoa.action_machine.domain.state_entity import BaseStateEntity
from aoa.action_machine.graph.validators.entity_specialization_validator import declared_entity_classes
from aoa.action_machine.intents.entity.entity_relation_intent_resolver import is_relation_container

__all__ = ["validate_entity_fields"]

_STRUCTURAL_BASES: tuple[tuple[type[Any], str], ...] = (
    (BaseCoreEntity, "Core"),
    (BaseAssocEntity, "Assoc"),
    (BaseDetailEntity, "Detail"),
    (BaseSpecEntity, "Spec"),
)
_RELATION_MARKERS: tuple[type[Any], ...] = (Inverse, NoInverse, NoGraphEdge)


def _kind_of(annotation: Any) -> str | None:
    """Return the structural kind ``annotation`` names, or ``None`` when it names none."""
    if not isinstance(annotation, type):
        return None
    for base, kind in _STRUCTURAL_BASES:
        if issubclass(annotation, base):
            return kind
    if issubclass(annotation, BaseStateEntity):
        return "State"
    return None


def _describe(annotation: Any) -> str:
    """Return a short readable name for an annotation."""
    name = getattr(annotation, "__name__", None)
    return str(name) if isinstance(name, str) else str(annotation)


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
    """Return the structural entity contained anywhere in ``annotation``, or ``None``."""
    if get_origin(annotation) is Annotated:
        return _entity_inside(get_args(annotation)[0])
    if _kind_of(annotation) is not None:
        return annotation
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
        f'(Annotated[AssociationMany[{name}], Inverse(...)]) or mark the field as an embedded value '
        f'(Annotated[{name}, NoRelation("reason")]).'
    )


def _refuse(entity_cls: type[BaseEntity], field_name: str, details: str) -> None:
    """Raise the declaration error for one field."""
    raise EntityFieldDeclarationError(entity_cls.__name__, field_name, details)


def _check_relation(
    entity_cls: type[BaseEntity], field_name: str, field_info: FieldInfo, annotation: Any
) -> bool:
    """Check a relation-container field and return whether the field was one."""
    if not is_relation_container(annotation):
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
            "NoRelation and a relation marker cannot be combined; the field either has a relation or "
            "it does not.",
        )
    inner, _optional = _strip_optional(annotation)
    kind = _kind_of(inner)
    if kind == "State":
        _refuse(entity_cls, field_name, _state_refusal(inner))
    if kind is None:
        _refuse(
            entity_cls,
            field_name,
            f"NoRelation marks an embedded value, so it applies only to a Core, Assoc, Detail or Spec "
            f"entity; this field's type is {_describe(annotation)}.",
        )
    return True


def _check_field(entity_cls: type[BaseEntity], field_name: str, field_info: FieldInfo) -> None:
    """Apply the declaration rule to one field."""
    annotation = field_info.annotation
    if _check_relation(entity_cls, field_name, field_info, annotation):
        return
    if _check_marker(entity_cls, field_name, field_info, annotation):
        return
    inner, allowed_none = _strip_optional(annotation)
    inner_kind = _kind_of(inner)
    if inner_kind == "State":
        _refuse(entity_cls, field_name, _state_refusal(inner))
    if inner_kind is not None:
        _refuse(entity_cls, field_name, _structural_refusal(inner, annotation))
    target = _entity_inside(annotation)
    if target is None:
        return
    if _kind_of(target) == "State":
        _refuse(entity_cls, field_name, _state_refusal(target))
    if allowed_none:
        _refuse(entity_cls, field_name, _structural_refusal(target, annotation))
    _refuse(entity_cls, field_name, _collection_refusal(target, annotation))


def validate_entity_fields(entities: list[type[BaseEntity]] | None = None) -> None:
    """
    Refuse every entity field that names a structural entity without declaring its form.

    Args:
        entities: classes to judge; when ``None``, every loaded ``@entity`` class is used.

    Raises:
        EntityFieldDeclarationError: a field is a bare entity, a collection of one, a bare
            optional of one, a state entity, or a misused embedded-value marker.
    """
    for entity_cls in declared_entity_classes() if entities is None else entities:
        for field_name, field_info in entity_cls.model_fields.items():
            _check_field(entity_cls, field_name, field_info)
