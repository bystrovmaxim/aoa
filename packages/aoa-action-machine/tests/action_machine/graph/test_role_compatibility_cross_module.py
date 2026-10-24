# packages/aoa-action-machine/tests/action_machine/graph/test_role_compatibility_cross_module.py
"""
Cross-module reciprocal declarations reach the role-pair check.

Postponed annotations and the composition root resolve both classes without circular
imports, and the role-pair validator then judges the resolved endpoints. Field-only
``Inverse(field_name=...)`` and concrete ``Inverse(Target, "...")`` receive the same
check.
"""

from __future__ import annotations

import textwrap

from ...support.isolated_entity_models import run_isolated_model

_PREAMBLE = textwrap.dedent(
    """
    import sys
    sys.path.insert(0, "packages/aoa-action-machine")

    from aoa.action_machine.graph.validators.entity_role_compatibility_validator import (
        validate_entity_role_compatibility,
    )
    from aoa.action_machine.domain.exceptions import RoleCompatibilityError
    """
)


def _run(body: str) -> str:
    result = run_isolated_model(_PREAMBLE + "\n" + textwrap.dedent(body))
    assert result.returncode == 0, result.stderr
    return result.stdout


def test_cross_module_resolved_pair_reaches_role_compatibility() -> None:
    """The two-module association pair resolves and passes the role check."""
    out = _run(
        """
        from tests.support.complete_relationships.offer import OfferCoreEntity
        from tests.support.complete_relationships.region import RegionCoreEntity

        OfferCoreEntity.model_rebuild(_types_namespace={"RegionCoreEntity": RegionCoreEntity})
        RegionCoreEntity.model_rebuild(_types_namespace={"OfferCoreEntity": OfferCoreEntity})
        validate_entity_role_compatibility([OfferCoreEntity, RegionCoreEntity])
        print("OK")
        """
    )
    assert "OK" in out


def test_field_only_and_concrete_inverse_receive_the_same_check() -> None:
    """One field-only and one concrete Inverse marker still reach the role check."""
    out = _run(
        """
        from typing import Annotated
        from pydantic import Field
        from aoa.action_machine.domain import (
            AssociationMany,
            AssociationOne,
            BaseCoreEntity,
            BaseDomain,
            Inverse,
        )
        from aoa.action_machine.intents.entity import entity

        class CrossDomain(BaseDomain):
            name = "cross2"
            description = "Cross 2"

        @entity(description="Offer", domain=CrossDomain)
        class OfferCoreEntity(BaseCoreEntity):
            id: str = Field(description="Identifier")
            regions: Annotated[AssociationMany[RegionCoreEntity], Inverse(RegionCoreEntity, "offer")] = Field(
                description="Regions"
            )

        @entity(description="Region", domain=CrossDomain)
        class RegionCoreEntity(BaseCoreEntity):
            id: str = Field(description="Identifier")
            offer: Annotated[AssociationOne[OfferCoreEntity], Inverse(field_name="regions")] = Field(
                description="Offer"
            )

        OfferCoreEntity.model_rebuild()
        RegionCoreEntity.model_rebuild()
        validate_entity_role_compatibility([OfferCoreEntity, RegionCoreEntity])
        print("OK")
        """
    )
    assert "OK" in out


def test_cross_module_ownership_pair_is_refused() -> None:
    """A resolved ownership/ownership pair is refused even across forward references."""
    out = _run(
        """
        from typing import Annotated
        from pydantic import Field
        from aoa.action_machine.domain import BaseCoreEntity, BaseDomain, CompositeMany, CompositeOne, Inverse
        from aoa.action_machine.intents.entity import entity

        class CrossDomain(BaseDomain):
            name = "cross3"
            description = "Cross 3"

        @entity(description="A", domain=CrossDomain)
        class ACoreEntity(BaseCoreEntity):
            id: str = Field(description="Identifier")
            b: Annotated[CompositeOne[BCoreEntity], Inverse(field_name="a")] = Field(description="B")

        @entity(description="B", domain=CrossDomain)
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
