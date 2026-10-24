# packages/aoa-action-machine/tests/action_machine/graph/test_role_compatibility_adversarial.py
"""
Adversarial regressions for the matrix: each mutation is caught while a control passes.

These tests pin the behaviour a mutation would break — admit an ownership/ownership pair,
admit an invalid specialized pair, reject a permitted Many pair. Each refused case sits beside
a valid neighbouring control, so a test that fails for the wrong reason is visible. The two
dictionary mutations of FR-027 are covered by the dictionary suite (T025).
"""

from __future__ import annotations

import textwrap

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
        BaseEnumEntity,
        BaseSpecEntity,
        Classifier,
        CompositeMany,
        CompositeOne,
        Generalization,
        Inverse,
        Specialization,
        value,
    )
    from aoa.action_machine.domain.exceptions import RoleCompatibilityError
    from aoa.action_machine.graph.validators.entity_role_compatibility_validator import (
        validate_entity_role_compatibility,
    )
    from aoa.action_machine.intents.entity import entity


    class AdvDomain(BaseDomain):
        name = "adv"
        description = "Adversarial"
    """
)


def _run(body: str) -> str:
    result = run_isolated_model(_IMPORTS + "\n" + textwrap.dedent(body))
    assert result.returncode == 0, result.stderr
    return result.stdout


def _run_pair(container_a: str, container_b: str) -> str:
    """Declare one reciprocal ordinary pair in a fresh process and return its verdict."""
    body = f"""
        @entity(description="First", domain=AdvDomain)
        class FirstCoreEntity(BaseCoreEntity):
            id: str = Field(description="Identifier")
            second: Annotated[{container_a}[SecondCoreEntity], Inverse(field_name="first")] = Field(
                description="Second"
            )

        @entity(description="Second", domain=AdvDomain)
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
        except RoleCompatibilityError:
            print("REFUSE")
    """
    return _run(body)


def test_admitting_an_ownership_over_ownership_pair_is_caught() -> None:
    """If the matrix admitted ownership/ownership, this refused case would accept."""
    assert "REFUSE" in _run_pair("CompositeOne", "CompositeMany")
    # Its valid neighbouring control keeps passing.
    assert "ACCEPT" in _run_pair("CompositeMany", "AssociationOne")


def test_rejecting_a_permitted_many_pair_is_caught() -> None:
    """Permitted Many pairs stay accepted; over-tightening the matrix fails here."""
    for pair in (
        ("CompositeMany", "AssociationOne"),
        ("AssociationMany", "AggregateMany"),
        ("AggregateMany", "AssociationOne"),
    ):
        assert "ACCEPT" in _run_pair(*pair), pair


def _run_valid_axis() -> str:
    """Declare a complete valid classified axis and return its verdict."""
    return _run(
        """
        @entity(description="Kind", domain=AdvDomain)
        class KindEnumEntity(BaseEnumEntity):
            FIRST = value(code="first", display_name="First")

        @entity(description="Head", domain=AdvDomain)
        class HeadCoreEntity(BaseCoreEntity):
            id: str = Field(description="Identifier")
            pressing: Annotated[
                Specialization[AltSpecEntity, KindEnumEntity],
                Inverse(field_name="record"),
            ] = Field(description="Details")

        @entity(description="Alt", domain=AdvDomain)
        class AltSpecEntity(BaseSpecEntity):
            id: str = Field(description="Identifier")
            record: Annotated[
                Generalization[HeadCoreEntity],
                Classifier(variant=KindEnumEntity.FIRST),
                Inverse(HeadCoreEntity, "pressing"),
            ] = Field(description="Record")

        HeadCoreEntity.model_rebuild()
        AltSpecEntity.model_rebuild()
        try:
            validate_entity_role_compatibility([HeadCoreEntity, AltSpecEntity, KindEnumEntity])
            print("ACCEPT")
        except RoleCompatibilityError:
            print("REFUSE")
        """
    )


def _run_generalization_pair() -> str:
    """Declare two Generalization fields pointing at each other and return the verdict."""
    return _run(
        """
        @entity(description="A", domain=AdvDomain)
        class ACoreEntity(BaseCoreEntity):
            id: str = Field(description="Identifier")
            b: Annotated[Generalization[BCoreEntity], Inverse(field_name="a")] = Field(description="B")

        @entity(description="B", domain=AdvDomain)
        class BCoreEntity(BaseCoreEntity):
            id: str = Field(description="Identifier")
            a: Annotated[Generalization[ACoreEntity], Inverse(field_name="b")] = Field(description="A")

        ACoreEntity.model_rebuild()
        BCoreEntity.model_rebuild()
        try:
            validate_entity_role_compatibility([ACoreEntity, BCoreEntity])
            print("ACCEPT")
        except RoleCompatibilityError:
            print("REFUSE")
        """
    )


def test_admitting_an_invalid_specialized_pair_is_caught() -> None:
    """A Generalization/Generalization pair is refused while a valid axis passes."""
    assert "REFUSE" in _run_generalization_pair()
    assert "ACCEPT" in _run_valid_axis()
