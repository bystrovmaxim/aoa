# packages/aoa-action-machine/src/aoa/action_machine/intents/entity/entity_specialization_intent_resolver.py
"""
EntitySpecializationIntentResolver — freeze one declared specialization axis from ``model_fields``.

╔═══════════════════════════════════════════════════════════════════════════════
║ PURPOSE
╚═══════════════════════════════════════════════════════════════════════════════

Read one head field that points at one of N extension entities, and hand the graph
and the build rules a plain description of it: which classes may be linked, which
field chooses among them, which codes exist, and what each code selects.

A field is a specialization axis when its type is a subscripted ``Specialization[...]``
container. The container is the discriminator, and it has to be: the ``Classifier``
marker appears on **both** sides — on the head naming the choosing field and the whole
code set, on each extension naming its own single code — so a marker alone never says
which side a field is on.

╔═══════════════════════════════════════════════════════════════════════════════
║ WHERE THE DATA LIVES — three places, and only two carry what we need
╚═══════════════════════════════════════════════════════════════════════════════

``model_fields[field].annotation``
    The container class pydantic built, e.g. ``Specialization[A | B]``. The
    alternatives are inside it, but ``get_args`` on that class returns nothing —
    pydantic materialises a real class — so they are read from
    ``__pydantic_generic_metadata__["args"]``.

``FieldInfo.metadata``
    The marker objects themselves: ``Classifier``, ``Inverse``, ``NoGraphEdge``.
    They are never in ``annotation``.

``get_type_hints(cls, include_extras=True)``
    Both together, and unusable here: it raises on a model whose forward references
    do not resolve, while ``model_fields`` stays readable. A parser that read the
    hints first would lose every axis on such a model.

The codes of the alternatives are not on the head at all. They are read from **the
other side**: each class in the union declares its own code on its reverse field, and
this resolver collects them into the ``code_to_target`` mapping everything else uses.

╔═══════════════════════════════════════════════════════════════════════════════
║ SCOPE (IN / OUT)
╚═══════════════════════════════════════════════════════════════════════════════

**In scope**
    Recognising a specialization field, and reading the axis out of it.
    Collecting each alternative's own code from its reverse field.
    Exposing ``code_to_target``, the mapping a resource, the graph and the ERD read.

**Out of scope**
    Checking the declaration rules — mutuality, closure, one head per class, code
    compatibility. They are decided across the whole model and belong to the build
    validator.
    Emitting graph nodes and edges, and drawing anything.

╔═══════════════════════════════════════════════════════════════════════════════
║ LIFECYCLE (IMPORT VS BUILD VS RUNTIME)
╚═══════════════════════════════════════════════════════════════════════════════

- **Import**: nothing runs; the row type and the helpers are defined.
- **Build**: ``gather_entity_specialization_intent_resolvers(cls)`` is called per
  entity class, by the graph node and by the validator.
- **Runtime**: the axis and its mapping are data; nothing here reads a row.

"""

from __future__ import annotations

import types
import typing
from dataclasses import dataclass, field
from typing import Any, get_args, get_origin

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


def _container_arguments_of(annotation: Any, container: type[Any]) -> tuple[Any, ...] | None:
    """
    Return the type arguments of a subscripted container, or ``None``.

    Pydantic turns ``Specialization[A | B]`` and ``Generalization[Head]`` into real
    classes, so ``get_args`` on them is empty; the arguments survive in
    ``__pydantic_generic_metadata__``.
    """
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
        if marker is not None and len(marker.code_values) == 1:
            return marker.code_values[0]
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
        declared = marker.code_values
        if len(declared) != 1:
            raise SpecializationDeclarationError(
                host_name,
                field_name,
                f"alternative '{target.__name__}' must declare exactly one code on its reverse field, "
                f"got {list(declared)}",
            )
        return declared[0]
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
            container but it declares no ``Classifier`` marker, or one alternative
            declares more than one code on its reverse field.
    """
    metadata = tuple(field_info.metadata)
    container_args = _container_arguments(annotation)
    if container_args is None:
        return None
    marker = _classifier_marker(metadata)

    host_name = host_cls.__name__

    if marker is None:
        raise SpecializationDeclarationError(
            host_name,
            field_name,
            "is a specialization container but declares no Classifier marker; "
            "name the choosing field and the codes beside it",
        )

    alternatives: list[type[Any]] = []
    for argument in container_args:
        alternatives.extend(_union_members(argument))

    codes = marker.code_values
    code_to_target: dict[str, type[Any]] = {}
    for target in alternatives:
        code = _reverse_code(target, host_cls, field_name, host_name)
        if code:
            code_to_target[code] = target

    return EntitySpecializationIntentResolver(
        field_name=field_name,
        head_entity=host_cls,
        classifier_field=marker.field,
        alternatives=tuple(alternatives),
        codes=tuple(codes),
        description=_field_description_hint(field_info),
        inverse_field=_inverse_field_name(metadata),
        code_to_target=code_to_target,
        deprecated=bool(getattr(field_info, "deprecated", False)),
        omit_graph_edge=any(isinstance(item, NoGraphEdge) for item in metadata),
    )


def _field_description_hint(field_info: FieldInfo) -> str:
    """Return the field's declared description, from ``Rel`` or from ``Field``."""
    from aoa.action_machine.domain.relation_markers import Rel  # pylint: disable=import-outside-toplevel

    default_val = field_info.default
    if isinstance(default_val, Rel):
        return default_val.description
    if field_info.description:
        return field_info.description
    return ""


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
