# packages/aoa-action-machine/tests/action_machine/graph/test_role_compatibility_bypass.py
"""
The role-pair check cannot be bypassed by presentation or inheritance.

``NoGraphEdge``, graph exclusion, and unchanged inheritance must not hide a refused
ownership/ownership pair: the check reads resolved descriptors, not graph edges, and
inherited endpoints are judged by their resolved declaring owner.
"""

from __future__ import annotations

import textwrap

from ...support.isolated_entity_models import run_isolated_model

_IMPORTS = textwrap.dedent(
    """
    from typing import Annotated

    from pydantic import Field

    from aoa.action_machine.domain import (
        BaseCoreEntity,
        BaseDomain,
        CompositeMany,
        CompositeOne,
        Inverse,
        NoGraphEdge,
    )
    from aoa.action_machine.domain.exceptions import RoleCompatibilityError
    from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
    from aoa.action_machine.graph.validators.entity_role_compatibility_validator import (
        validate_entity_role_compatibility,
    )
    from aoa.action_machine.intents.entity import entity


    class CompatDomain(BaseDomain):
        name = "compat"
        description = "Compatibility"
    """
)


def _run(body: str) -> str:
    result = run_isolated_model(_IMPORTS + "\n" + textwrap.dedent(body))
    assert result.returncode == 0, result.stderr
    return result.stdout


def test_no_graph_edge_does_not_bypass_the_check() -> None:
    """A hidden edge on one endpoint still refuses the ownership/ownership pair."""
    out = _run(
        """
        @entity(description="A", domain=CompatDomain)
        class ACoreEntity(BaseCoreEntity):
            id: str = Field(description="Identifier")
            b: Annotated[CompositeOne[BCoreEntity], Inverse(field_name="a"), NoGraphEdge()] = Field(
                description="B"
            )

        @entity(description="B", domain=CompatDomain)
        class BCoreEntity(BaseCoreEntity):
            id: str = Field(description="Identifier")
            a: Annotated[CompositeMany[ACoreEntity], Inverse(field_name="b")] = Field(description="A")

        ACoreEntity.model_rebuild()
        BCoreEntity.model_rebuild()
        try:
            validate_entity_role_compatibility([ACoreEntity, BCoreEntity])
            print("ACCEPT")
        except RoleCompatibilityError:
            print("REFUSE")
        """
    )
    assert "REFUSE" in out


def test_graph_exclusion_does_not_bypass_the_check() -> None:
    """A graph-excluded ownership/ownership pair is still refused on full assembly."""
    out = _run(
        """
        @exclude_graph_model
        @entity(description="A", domain=CompatDomain)
        class ACoreEntity(BaseCoreEntity):
            id: str = Field(description="Identifier")
            b: Annotated[CompositeOne[BCoreEntity], Inverse(field_name="a")] = Field(description="B")

        @exclude_graph_model
        @entity(description="B", domain=CompatDomain)
        class BCoreEntity(BaseCoreEntity):
            id: str = Field(description="Identifier")
            a: Annotated[CompositeMany[ACoreEntity], Inverse(field_name="b")] = Field(description="A")

        ACoreEntity.model_rebuild()
        BCoreEntity.model_rebuild()
        try:
            validate_entity_role_compatibility()
            print("ACCEPT")
        except RoleCompatibilityError:
            print("REFUSE")
        """
    )
    assert "REFUSE" in out


def test_an_unchanged_inherited_pair_keeps_its_base_roles() -> None:
    """A child inheriting an ownership endpoint is judged by the base resolved role."""
    out = _run(
        """
        @entity(description="A", domain=CompatDomain)
        class ACoreEntity(BaseCoreEntity):
            id: str = Field(description="Identifier")
            b: Annotated[CompositeOne[BCoreEntity], Inverse(field_name="a")] = Field(description="B")

        @entity(description="B", domain=CompatDomain)
        class BCoreEntity(BaseCoreEntity):
            id: str = Field(description="Identifier")
            a: Annotated[CompositeMany[ACoreEntity], Inverse(field_name="b")] = Field(description="A")

        @entity(description="ChildA", domain=CompatDomain)
        class ChildACoreEntity(ACoreEntity):
            extra: str = Field(description="Extra")

        ACoreEntity.model_rebuild()
        BCoreEntity.model_rebuild()
        ChildACoreEntity.model_rebuild()
        try:
            validate_entity_role_compatibility([ChildACoreEntity, BCoreEntity])
            print("ACCEPT")
        except RoleCompatibilityError:
            print("REFUSE")
        """
    )
    assert "REFUSE" in out
