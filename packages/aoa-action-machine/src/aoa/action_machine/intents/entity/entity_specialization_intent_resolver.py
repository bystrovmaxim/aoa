# packages/aoa-action-machine/src/aoa/action_machine/intents/entity/entity_specialization_intent_resolver.py
"""
EntitySpecializationIntentResolver — read an axis and its dictionary.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Read a head's ``Specialization[Alternatives, Dictionary]`` field, including an
optional field, into a description used by graph construction and validation.
An axis is one such field together with its dictionary and alternative classes.
The dictionary supplies code order; the alternatives' reverse ``Classifier``
markers supply the code-to-class correspondence. Union position does not assign
codes. ``Generalization[Head]`` identifies the reverse target.

This module reads declarations; it neither loads rows nor proves their validity.
The declaration validator checks coverage, value membership and relationship
consistency. ``classifier_field`` remains an empty compatibility attribute on the
resolver result; no selector field is part of the declaration or graph edge.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    head field -> container arguments -> alternatives + dictionary.codes()
    alternative reverse fields -------> code_to_target
                                        |
                                        v
                         declaration validator and graph edges
"""

from __future__ import annotations

import types
import typing
from dataclasses import dataclass, field
from typing import Any, cast, get_args, get_origin

from pydantic.fields import FieldInfo

from aoa.action_machine.domain.exceptions import SpecializationDeclarationError
from aoa.action_machine.domain.relation_markers import Inverse, NoGraphEdge
from aoa.action_machine.domain.specialization_containers import Classifier, Generalization, Specialization


@dataclass(frozen=True)
class EntitySpecializationIntentResolver:
    """
    One specialization axis of a head entity: its alternatives, codes and classifier.

    ``alternatives`` and ``codes`` are in declaration order, and position pairs them
    for reading. The build checks them by membership, not by position, so reordering
    one list alone never breaks a model.
    """

    field_name: str
    head_entity: type[Any]
    classifier_field: str
    alternatives: tuple[type[Any], ...]
    codes: tuple[str, ...]
    description: str = ""
    inverse_field: str = ""
    code_to_target: dict[str, type[Any]] = field(default_factory=dict)
    deprecated: bool = False
    omit_graph_edge: bool = False
    dictionary: type[Any] | None = None


def _container_arguments_of(annotation: Any, container: type[Any]) -> tuple[Any, ...] | None:
    """
    Return the type arguments of a subscripted container, or ``None``.

    Pydantic turns ``Specialization[A | B, Dictionary]`` and ``Generalization[Head]`` into real
    classes, so ``get_args`` on them is empty; the arguments survive in
    ``__pydantic_generic_metadata__``.
    """
    if get_origin(annotation) in (typing.Union, types.UnionType):
        members = tuple(arg for arg in get_args(annotation) if arg is not types.NoneType)
        if len(members) == 1:
            return _container_arguments_of(members[0], container)
    if not (isinstance(annotation, type) and issubclass(annotation, container)):
        return None
    metadata = getattr(annotation, "__pydantic_generic_metadata__", None)
    if not isinstance(metadata, dict):
        return None
    return tuple(metadata.get("args") or ())


def _container_arguments(annotation: Any) -> tuple[Any, ...] | None:
    """Return the type arguments of a subscripted ``Specialization``, or ``None``."""
    return _container_arguments_of(annotation, Specialization)


def _union_members(typ: Any) -> tuple[type[Any], ...]:
    """Flatten a union into its members, leaving a single type as a one-tuple."""
    origin = get_origin(typ)
    if origin is types.UnionType or origin is typing.Union:
        return tuple(arg for arg in get_args(typ) if arg is not types.NoneType)
    return (typ,)


def _classifier_marker(metadata: tuple[Any, ...]) -> Classifier | None:
    """Return the ``Classifier`` marker of a field, if it carries one."""
    for item in metadata:
        if isinstance(item, Classifier):
            return item
    return None


def _inverse_field_name(metadata: tuple[Any, ...]) -> str:
    """Return the partner field name named by ``Inverse``, or an empty string."""
    for item in metadata:
        if isinstance(item, Inverse):
            return str(item.field_name)
    return ""


def is_specialization_field(annotation: Any) -> bool:
    """
    True when the field's type is a subscripted ``Specialization`` container.

    The container alone decides. A ``Classifier`` marker also sits on every extension's
    reverse field, where it names that class's own code, so the marker cannot be the
    test — and a field that carries the marker without the container is simply the
    other side of an axis.

    Public because the graph's scalar-field path asks the same question. A
    specialization field stays a column **and** becomes a relation, and both answers
    must come from one place instead of two that can drift. The question is about the
    annotation alone, so nothing is read and nothing can raise.
    """
    return _container_arguments(annotation) is not None


def reverse_head(target: type[Any], field_info: FieldInfo) -> type[Any] | None:
    """
    Return the head a reverse field points at, or ``None`` when it points at none.

    The head is the container's type argument — ``Generalization[HeadEntity]`` — read
    the same way as the head's own alternatives, because the container is a real class.
    """
    arguments = _container_arguments_of(field_info.annotation, Generalization)
    if not arguments:
        return None
    members = _union_members(arguments[0])
    return members[0] if members else None


def read_reverse_declarations(target: type[Any], head_entity: type[Any]) -> list[tuple[str, FieldInfo]]:
    """
    Return ``(field_name, field_info)`` for every field of ``target`` that points at ``head_entity``.

    These are the fields a ``Generalization`` container lives on, and they are how every consumer
    finds an extension's own side of an axis: the code it declares, the field name the head's
    ``Inverse`` names, and the fact that the class is reachable from its head at all. Public
    because three places read it — the parser, the build validator and the graph edge — and three
    readings of one declaration is how a model starts contradicting its own documentation.
    """
    model_fields = getattr(target, "model_fields", None)
    if not model_fields:
        return []
    return [
        (name, info) for name, info in model_fields.items() if reverse_head(target, info) is head_entity
    ]


def read_declared_code(target: type[Any], head_entity: type[Any], *, field_name: str = "") -> str:
    """
    Return the single code ``target`` declares for the axis whose head is ``head_entity``.

    Returns an empty string when the class declares no reverse field for this head, or a reverse
    field with no code on it. Both are states the build refuses, so a caller that has run the
    validator never sees them; a caller that has not gets an empty answer rather than an exception,
    because "which code is declared" is a question and not a check.
    """
    for name, info in read_reverse_declarations(target, head_entity):
        if field_name and name != field_name:
            continue
        marker = _classifier_marker(tuple(info.metadata))
        if marker is None:
            continue
        return str(marker.variant.code)
    return ""


def _reverse_code(target: type[Any], head_entity: type[Any], field_name: str, host_name: str) -> str:
    """
    Read one alternative's own code from the field that points back at its head.

    Args:
        target: The alternative class named by the head's container.
        head_entity: The head class the reverse field must point back at.
        field_name: The head's field, for diagnostics.
        host_name: The head class name, for diagnostics.

    Returns:
        The code the alternative declares, or an empty string when it declares none.

    Raises:
        SpecializationDeclarationError: The alternative declares more than one code
            on the field that points at this head.
    """
    model_fields = getattr(target, "model_fields", None)
    if not model_fields:
        return ""

    for candidate in model_fields.values():
        if reverse_head(target, candidate) is not head_entity:
            continue
        marker = _classifier_marker(tuple(candidate.metadata))
        if marker is None:
            return ""
        return str(marker.variant.code)
    return ""


def _axis_from_field(
    host_cls: type[Any],
    field_name: str,
    annotation: Any,
    field_info: FieldInfo,
) -> EntitySpecializationIntentResolver | None:
    """
    Parse one field into an axis row, or ``None`` when it is not a specialization field.

    Raises:
        SpecializationDeclarationError: The field's type is a ``Specialization``
            container whose second type argument is not a closed dictionary.
    """
    metadata = tuple(field_info.metadata)
    container_args = _container_arguments(annotation)
    if container_args is None:
        return None
    host_name = host_cls.__name__

    # pylint: disable-next=import-outside-toplevel  # a module-level import would close a cycle
    from aoa.action_machine.domain.enum_entity import BaseEnumEntity

    second = container_args[1] if len(container_args) == 2 else None
    dictionary: type[Any] | None = None
    if isinstance(second, type) and issubclass(second, BaseEnumEntity):
        dictionary = second
    else:
        raise SpecializationDeclarationError(
            host_name,
            field_name,
            "is a specialization container whose second type argument is not a closed "
            "dictionary; write Specialization[Alternatives, Dictionary]",
        )

    alternatives: list[type[Any]] = []
    for argument in container_args[:1]:
        alternatives.extend(_union_members(argument))

    codes = tuple(cast(Any, dictionary).codes())
    code_to_target: dict[str, type[Any]] = {}
    for target in alternatives:
        code = _reverse_code(target, host_cls, field_name, host_name)
        if code:
            code_to_target[code] = target

    return EntitySpecializationIntentResolver(
        field_name=field_name,
        head_entity=host_cls,
        classifier_field="",
        alternatives=tuple(alternatives),
        codes=tuple(codes),
        description=_field_description_hint(field_info),
        inverse_field=_inverse_field_name(metadata),
        code_to_target=code_to_target,
        deprecated=bool(getattr(field_info, "deprecated", False)),
        omit_graph_edge=any(isinstance(item, NoGraphEdge) for item in metadata),
        dictionary=dictionary,
    )


def _field_description_hint(field_info: FieldInfo) -> str:
    """Return the description the field carries in its own metadata."""
    return field_info.description or ""


def gather_entity_specialization_intent_resolvers(host_cls: type) -> list[EntitySpecializationIntentResolver]:
    """Return every specialization axis declared on ``host_cls``, in field order."""
    model_fields = getattr(host_cls, "model_fields", None)
    if not model_fields:
        return []

    out: list[EntitySpecializationIntentResolver] = []
    for field_name, field_info in model_fields.items():
        resolved = _axis_from_field(host_cls, field_name, field_info.annotation, field_info)
        if resolved is not None:
            out.append(resolved)
    return out
