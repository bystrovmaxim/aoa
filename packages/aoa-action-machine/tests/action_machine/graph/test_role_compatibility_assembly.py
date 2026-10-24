# packages/aoa-action-machine/tests/action_machine/graph/test_role_compatibility_assembly.py
"""
Role-pair matrix enforced on actual reciprocal declarations.

Each permitted family is accepted and each prohibited family is refused before
publication, through the same public validator the graph coordinator calls. Every
declaration is built in a fresh interpreter so an invalid pair never poisons another
model.
"""

from __future__ import annotations

import textwrap

import pytest

from ...support.isolated_entity_models import run_isolated_model

_IMPORTS = textwrap.dedent(
    """
    from typing import Annotated

    from pydantic import Field

    from aoa.action_machine.domain import (
        AggregateMany,
        AggregateOne,
        AssociationMany,
        AssociationOne,
        BaseCoreEntity,
        BaseDomain,
        CompositeMany,
        CompositeOne,
        Inverse,
    )
    from aoa.action_machine.domain.exceptions import RoleCompatibilityError
    from aoa.action_machine.graph.validators.entity_role_compatibility_validator import (
        validate_entity_role_compatibility,
    )
    from aoa.action_machine.intents.entity import entity


    class CompatDomain(BaseDomain):
        name = "compat"
        description = "Compatibility"
    """
)


def _run_pair(container_a: str, container_b: str) -> str:
    """Declare one reciprocal pair in a fresh process and return its verdict."""
    body = f"""
        @entity(description="First", domain=CompatDomain)
        class FirstCoreEntity(BaseCoreEntity):
            id: str = Field(description="Identifier")
            second: Annotated[{container_a}[SecondCoreEntity], Inverse(field_name="first")] = Field(
                description="Second"
            )

        @entity(description="Second", domain=CompatDomain)
        class SecondCoreEntity(BaseCoreEntity):
            id: str = Field(description="Identifier")
            first: Annotated[{container_b}[FirstCoreEntity], Inverse(field_name="second")] = Field(
                description="First"
            )

        FirstCoreEntity.model_rebuild()
        SecondCoreEntity.model_rebuild()
        try:
            validate_entity_role_compatibility([FirstCoreEntity, SecondCoreEntity])
            print("ACCEPT")
        except RoleCompatibilityError as exc:
            print("REFUSE " + exc.first_role + " " + exc.second_role + " :: " + exc.rule + " :: " + exc.correction)
    """
    result = run_isolated_model(_IMPORTS + "\n" + textwrap.dedent(body))
    assert result.returncode == 0, result.stderr
    return result.stdout


_PERMITTED = [
    ("AssociationOne", "AssociationOne"),
    ("AssociationOne", "AssociationMany"),
    ("AssociationMany", "AssociationMany"),
    ("AssociationOne", "AggregateOne"),
    ("AssociationMany", "AggregateOne"),
    ("AssociationOne", "CompositeOne"),
    ("CompositeMany", "AssociationOne"),
    ("AggregateMany", "AssociationOne"),
]

_PROHIBITED = [
    ("AggregateOne", "AggregateOne"),
    ("AggregateMany", "AggregateOne"),
    ("CompositeOne", "CompositeOne"),
    ("CompositeOne", "CompositeMany"),
    ("CompositeOne", "AggregateOne"),
]


@pytest.mark.parametrize(("container_a", "container_b"), _PERMITTED)
def test_permitted_pair_is_accepted(container_a: str, container_b: str) -> None:
    """A permitted role pair publishes; no compatibility error is raised."""
    out = _run_pair(container_a, container_b)
    assert "ACCEPT" in out, f"{container_a} <-> {container_b} was refused: {out}"


@pytest.mark.parametrize(("container_a", "container_b"), _PROHIBITED)
def test_prohibited_pair_is_refused(container_a: str, container_b: str) -> None:
    """A prohibited role pair is refused with the ownership rule."""
    out = _run_pair(container_a, container_b)
    assert "REFUSE" in out, f"{container_a} <-> {container_b} was accepted: {out}"


def test_ownership_refusal_names_the_ownership_rule() -> None:
    """A CompositeOne/CompositeMany refusal says both endpoints carry ownership roles."""
    out = _run_pair("CompositeOne", "CompositeMany")
    assert "ownership" in out
    assert "AssociationOne or AssociationMany" in out


def test_a_valid_association_pair_is_the_neighbouring_control() -> None:
    """A permitted Many pair stays accepted beside the ownership refusal."""
    out = _run_pair("CompositeMany", "AssociationOne")
    assert "ACCEPT" in out
