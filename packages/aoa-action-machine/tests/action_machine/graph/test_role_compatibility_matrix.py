# packages/aoa-action-machine/tests/action_machine/graph/test_role_compatibility_matrix.py
"""
Role-pair matrix: all 64 directed cells, symmetry, and cardinality independence.

The eight roles form the symmetric 8×8 matrix: exactly 22 directed cells are permitted
and 42 are refused. One/Many never changes a verdict, and specialization pairs only with
generalization. These assertions run in-process over the pure lookup, so they never
declare an entity.
"""

from __future__ import annotations

from aoa.action_machine.domain import (
    AggregateMany,
    AggregateOne,
    AssociationMany,
    AssociationOne,
    CompositeMany,
    CompositeOne,
    Generalization,
    Specialization,
)
from aoa.action_machine.graph.validators.entity_role_compatibility_validator import (
    ROLES,
    role_of,
    roles_compatible,
)


def test_all_64_directed_cells_match_the_matrix() -> None:
    """Exactly 22 directed cells are permitted and 42 are refused."""
    permitted = [(a, b) for a in ROLES for b in ROLES if roles_compatible(a, b)]
    refused = [(a, b) for a in ROLES for b in ROLES if not roles_compatible(a, b)]

    assert len(permitted) == 22, len(permitted)
    assert len(refused) == 42, len(refused)


def test_compatibility_is_symmetric() -> None:
    """Swapping the endpoints preserves the verdict."""
    for first in ROLES:
        for second in ROLES:
            assert roles_compatible(first, second) == roles_compatible(second, first)


def test_cardinality_never_changes_a_verdict() -> None:
    """One and Many describe cardinality only; the family decides."""
    assert roles_compatible("CompositeOne", "AssociationMany") is True
    assert roles_compatible("CompositeMany", "AssociationOne") is True
    assert roles_compatible("AggregateOne", "AssociationMany") is True
    assert roles_compatible("AggregateMany", "AssociationOne") is True
    assert roles_compatible("CompositeOne", "CompositeMany") is False
    assert roles_compatible("AggregateOne", "AggregateMany") is False
    assert roles_compatible("AggregateOne", "CompositeMany") is False


def test_specialization_pairs_only_with_generalization() -> None:
    """Spec/gen pair exclusively; same-role and ordinary-role pairings are refused."""
    assert roles_compatible("Specialization", "Generalization") is True

    assert roles_compatible("Specialization", "Specialization") is False
    assert roles_compatible("Generalization", "Generalization") is False
    for role in ROLES:
        if role not in ("Specialization", "Generalization"):
            assert roles_compatible("Specialization", role) is False
            assert roles_compatible("Generalization", role) is False


def test_role_of_maps_all_eight_containers() -> None:
    """Each container resolves to its role name; an unknown class resolves to None."""
    expected = {
        AssociationOne: "AssociationOne",
        AssociationMany: "AssociationMany",
        AggregateOne: "AggregateOne",
        AggregateMany: "AggregateMany",
        CompositeOne: "CompositeOne",
        CompositeMany: "CompositeMany",
        Specialization: "Specialization",
        Generalization: "Generalization",
    }
    for container, role in expected.items():
        assert role_of(container) == role
    assert role_of(int) is None
