# packages/aoa-action-machine/src/aoa/action_machine/graph/validators/entity_inverse_validator.py
"""
EntityInverseValidator — require reciprocal ``Inverse`` declarations for every paired relation.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A field that declares ``Inverse`` names its reverse field; that reverse field must exist on
the resolved target, declare its own ``Inverse`` and name this endpoint back. A one-sided
``Inverse``, an ``Inverse`` paired with ``NoInverse``, a missing reverse field, a mismatched
concrete target and a non-reciprocal pair all fail before publication.

═══════════════════════════════════════════════════════════════════════════════
RULES
═══════════════════════════════════════════════════════════════════════════════

- Endpoints are compared by canonical ``(declaring_owner_class_identity, field_name)``.
- ``Inverse(Target, "field")`` must name the resolved container target by identity.
- ``Inverse(field_name="field")`` resolves its target from the container's type argument.
- ``NoInverse()`` declares an unpaired field; it can never be the reverse of an ``Inverse``.
- An unchanged inherited field keeps its base declaring owner for reciprocity.

═══════════════════════════════════════════════════════════════════════════════
LIFECYCLE
═══════════════════════════════════════════════════════════════════════════════

- **Build**: runs after the completeness pass and before graph node construction; reads
  descriptors, never graph constructors, so cyclic models cannot recurse.
"""

from __future__ import annotations

from typing import Any

from aoa.action_machine.domain.entity import BaseEntity
from aoa.action_machine.domain.exceptions import EntityFieldDeclarationError
from aoa.action_machine.domain.relation_markers import Inverse
from aoa.action_machine.intents.entity.entity_intent import entity_info_is_set
from aoa.action_machine.intents.entity.resolved_entity_fields import (
    ResolvedEntityField,
    resolve_entity_field,
    resolve_entity_fields,
)

__all__ = ["validate_entity_inverses"]


def _all_declared_entity_classes() -> list[type[BaseEntity]]:
    """Return every ``@entity`` class, including graph-excluded hosts."""
    found: dict[str, type[BaseEntity]] = {}
    pending: list[type[Any]] = [BaseEntity]
    seen: set[type[Any]] = set()
    while pending:
        current = pending.pop()
        if current in seen:
            continue
        seen.add(current)
        for subclass in current.__subclasses__():
            pending.append(subclass)
            if entity_info_is_set(subclass):
                found[f"{subclass.__module__}.{subclass.__qualname__}"] = subclass
    return [found[key] for key in sorted(found)]


def _refuse(field: ResolvedEntityField, details: str) -> None:
    """Raise the declaration error for one non-reciprocal endpoint."""
    raise EntityFieldDeclarationError(field.effective_host.__name__, field.field_name, details)


def _concrete_marker_target(field: ResolvedEntityField) -> type[Any] | None:
    """Return the concrete target a field's ``Inverse`` marker names, or ``None``."""
    for item in field.metadata:
        if isinstance(item, Inverse) and item.target_entity is not None:
            return item.target_entity
    return None


def _reverse_field(target_entity: type[Any], field_name: str) -> ResolvedEntityField | None:
    """Resolve the reverse field on ``target_entity``, or ``None`` when it does not exist."""
    model_fields = getattr(target_entity, "model_fields", None)
    if not model_fields or field_name not in model_fields:
        return None
    return resolve_entity_field(target_entity, field_name, model_fields[field_name])


def _check_reciprocal(field: ResolvedEntityField) -> None:
    """Verify that ``field``'s ``Inverse`` endpoint names ``field`` back."""
    target_entity = field.inverse_entity
    reverse_field_name = field.inverse_field

    if target_entity is None:
        _refuse(
            field,
            "the field declares Inverse but its target cannot be resolved from the container; "
            "name the target explicitly or resolve the container type argument.",
        )
        return

    concrete = _concrete_marker_target(field)
    if concrete is not None and field.targets and concrete is not field.targets[0]:
        _refuse(
            field,
            f"the concrete Inverse target ({concrete.__name__}) does not match the resolved "
            f"container target ({field.targets[0].__name__}); write Inverse(field_name=...) or "
            f"name the resolved target.",
        )
        return

    if reverse_field_name is None:
        _refuse(field, "the Inverse marker names no reverse field.")
        return
    reverse = _reverse_field(target_entity, reverse_field_name)
    if reverse is None:
        _refuse(
            field,
            f"the field names inverse field '{reverse_field_name}' on {target_entity.__name__}, "
            f"but that field does not exist; add it, or declare NoInverse() for a one-way edge.",
        )
        return

    if not reverse.has_inverse:
        _refuse(
            field,
            f"the reverse field '{reverse_field_name}' on {target_entity.__name__} declares no "
            f"Inverse (it is NoInverse or missing a direction marker); declare a reciprocal "
            f"Inverse(...) on both endpoints.",
        )
        return

    if reverse.inverse_entity is not field.declaring_owner:
        _refuse(
            field,
            f"the reverse field '{reverse_field_name}' on {target_entity.__name__} points back to "
            f"{getattr(reverse.inverse_entity, '__name__', reverse.inverse_entity)}, not to "
            f"{field.declaring_owner.__name__}; each endpoint must name the other.",
        )
        return

    if reverse.inverse_field != field.field_name:
        _refuse(
            field,
            f"the reverse field '{reverse_field_name}' on {target_entity.__name__} points back to "
            f"field '{reverse.inverse_field}', not '{field.field_name}'.",
        )


def validate_entity_inverses(entities: list[type[BaseEntity]] | None = None) -> None:
    """
    Refuse every ``Inverse`` field whose reverse endpoint does not name it back.

    Args:
        entities: classes to judge; when ``None``, every loaded ``@entity`` class is used,
            including graph-excluded hosts.

    Raises:
        EntityFieldDeclarationError: a one-sided inverse, an ``Inverse`` paired with
            ``NoInverse``, a missing reverse field, a concrete-target mismatch or a
            non-reciprocal pair.
    """
    hosts = _all_declared_entity_classes() if entities is None else entities
    for host in hosts:
        for field in resolve_entity_fields(host):
            # Specialization/generalization reciprocity is checked by the specialization
            # validator, which reads the alternatives' reverse declarations, not this pass.
            if field.has_inverse and field.is_relation:
                _check_reciprocal(field)
