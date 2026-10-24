# packages/aoa-action-machine/src/aoa/action_machine/graph/validators/entity_role_compatibility_validator.py
"""
EntityRoleCompatibilityValidator — refuse prohibited endpoint role pairs.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Every explicitly paired relationship declares two endpoint roles, one per field.
The two resolved roles are validated against the symmetric role-pair matrix: an
ownership/ownership pair (aggregate/aggregate, composite/composite,
aggregate/composite) and a specialization/generalization endpoint paired with an
ordinary role are refused before the graph is published. Cardinality (One/Many)
never changes a verdict.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    resolved field -> container -> role name -> family -> matrix lookup
                                                          |
                                                          v
                                              permitted pair or RoleCompatibilityError

The matrix is a family-level lookup over the eight role names, so the eight rows
and columns of the 8×8 table fall out of the same rule.

═══════════════════════════════════════════════════════════════════════════════
LIFECYCLE (IMPORT VS BUILD VS RUNTIME)
═══════════════════════════════════════════════════════════════════════════════

- **Build**: runs after the completeness and inverse passes and before graph node
  construction, so a refused role pair blocks publication while an earlier
  declaration failure is still reported first by its own pass.
"""

from __future__ import annotations

from typing import Any

from aoa.action_machine.domain.entity import BaseEntity
from aoa.action_machine.domain.exceptions import RoleCompatibilityError
from aoa.action_machine.domain.relation_containers import (
    AggregateMany,
    AggregateOne,
    AssociationMany,
    AssociationOne,
    CompositeMany,
    CompositeOne,
)
from aoa.action_machine.domain.specialization_containers import Generalization, Specialization
from aoa.action_machine.intents.entity.entity_intent import entity_info_is_set
from aoa.action_machine.intents.entity.resolved_entity_fields import (
    ResolvedEntityField,
    resolve_entity_field,
    resolve_entity_fields,
)

__all__ = ["ROLES", "role_of", "roles_compatible", "validate_entity_role_compatibility"]

# The eight endpoint roles, in matrix order.
ROLES: tuple[str, ...] = (
    "AssociationOne",
    "AssociationMany",
    "AggregateOne",
    "AggregateMany",
    "CompositeOne",
    "CompositeMany",
    "Specialization",
    "Generalization",
)

# Each role mapped to the compatibility family it belongs to. Cardinality (One/Many)
# is part of the role name but not of the family: it never changes a matrix verdict.
_ROLE_FAMILY: dict[str, str] = {
    "AssociationOne": "association",
    "AssociationMany": "association",
    "AggregateOne": "aggregate",
    "AggregateMany": "aggregate",
    "CompositeOne": "composite",
    "CompositeMany": "composite",
    "Specialization": "specialization",
    "Generalization": "generalization",
}

# The resolved container class each role name belongs to.
_ROLE_OF_CONTAINER: dict[type[Any], str] = {
    AssociationOne: "AssociationOne",
    AssociationMany: "AssociationMany",
    AggregateOne: "AggregateOne",
    AggregateMany: "AggregateMany",
    CompositeOne: "CompositeOne",
    CompositeMany: "CompositeMany",
    Specialization: "Specialization",
    Generalization: "Generalization",
}

# The symmetric role-pair matrix as a family-level rule: a pair is permitted when its
# two families form one of these pairs, in either order. Twelve unordered
# combinations are permitted and twenty-four are refused; the directed 8×8 table
# contains 22 permitted and 42 prohibited cells.
_ALLOWED_FAMILY_PAIRS: frozenset[tuple[str, str]] = frozenset(
    {
        ("association", "association"),
        ("association", "aggregate"),
        ("association", "composite"),
        ("specialization", "generalization"),
    }
)

_SPECIALIZATION_ROLES: frozenset[str] = frozenset({"Specialization", "Generalization"})


def role_of(container: type[Any] | None) -> str | None:
    """Return the role name a relation container declares, or ``None``."""
    if container is None:
        return None
    return _ROLE_OF_CONTAINER.get(container)


def roles_compatible(first_role: str, second_role: str) -> bool:
    """Return whether two endpoint roles form a permitted pair of the matrix."""
    first_family = _ROLE_FAMILY[first_role]
    second_family = _ROLE_FAMILY[second_role]
    pair = (first_family, second_family)
    return pair in _ALLOWED_FAMILY_PAIRS or (second_family, first_family) in _ALLOWED_FAMILY_PAIRS


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


def _reverse_field(target_entity: type[Any] | None, field_name: str | None) -> ResolvedEntityField | None:
    """Resolve the reverse field on ``target_entity``, or ``None`` when it does not exist."""
    if target_entity is None or field_name is None:
        return None
    model_fields = getattr(target_entity, "model_fields", None)
    if not model_fields or field_name not in model_fields:
        return None
    return resolve_entity_field(target_entity, field_name, model_fields[field_name])


def _diagnose(first_role: str, second_role: str) -> tuple[str, str]:
    """Return the (rule, correction) a refused role pair violates."""
    if first_role in _SPECIALIZATION_ROLES or second_role in _SPECIALIZATION_ROLES:
        return (
            "Specialization and Generalization pair exclusively with each other",
            "declare the reverse endpoint as the matching Specialization or Generalization role",
        )
    return (
        "both endpoints carry ownership roles",
        "the reverse of an ownership endpoint must be AssociationOne or AssociationMany; "
        "change one of these two endpoints to an association role according to which side "
        "owns the other in your domain",
    )


def _reverse_endpoints(field: ResolvedEntityField) -> list[ResolvedEntityField]:
    """Return the resolved reverse endpoints of one paired field."""
    if field.is_specialization:
        # A head names one reverse field name on every alternative it declares.
        return [
            reverse
            for alternative in field.targets
            if (reverse := _reverse_field(alternative, field.inverse_field)) is not None
        ]
    reverse = _reverse_field(field.inverse_entity, field.inverse_field)
    return [reverse] if reverse is not None else []


def _check_role_pair(field: ResolvedEntityField) -> None:
    """Refuse a reciprocal pair whose two resolved roles the matrix prohibits."""
    first_role = role_of(field.container)
    if first_role is None:
        return  # unresolved container; the completeness pass reports it first

    for reverse in _reverse_endpoints(field):
        if not reverse.has_inverse:
            continue  # non-reciprocal; the inverse pass reports it first

        second_role = role_of(reverse.container)
        if second_role is None:
            continue

        if roles_compatible(first_role, second_role):
            continue

        rule, correction = _diagnose(first_role, second_role)
        raise RoleCompatibilityError(
            first_entity=field.declaring_owner.__name__,
            first_field=field.field_name,
            second_entity=reverse.declaring_owner.__name__,
            second_field=reverse.field_name,
            first_role=first_role,
            second_role=second_role,
            rule=rule,
            correction=correction,
        )


def validate_entity_role_compatibility(entities: list[type[BaseEntity]] | None = None) -> None:
    """
    Refuse every reciprocal pair whose two resolved roles the matrix prohibits.

    Args:
        entities: classes to judge; when ``None``, every loaded ``@entity`` class is used,
            including graph-excluded hosts.

    Raises:
        RoleCompatibilityError: an ownership/ownership pair or a specialization/
            generalization endpoint paired with an ordinary role.
    """
    hosts = _all_declared_entity_classes() if entities is None else entities
    for host in hosts:
        for field in resolve_entity_fields(host):
            if field.has_inverse and (field.is_relation or field.is_specialization or field.is_generalization):
                _check_role_pair(field)
