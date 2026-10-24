# packages/aoa-action-machine/tests/action_machine/graph/test_role_compatibility_specialization.py
"""
Specialization pairs only with Generalization.

A complete valid axis passes the role check; a specialization or generalization endpoint
paired with an ordinary role is refused with the "pair exclusively" message. The matrix-level
Spec/Spec and Gen/Gen refusals are asserted directly over the pure lookup.
"""

from __future__ import annotations

import textwrap

from aoa.action_machine.graph.validators.entity_role_compatibility_validator import roles_compatible

from ...support.isolated_entity_models import run_isolated_model

_IMPORTS = textwrap.dedent(
    """
    from typing import Annotated

    from pydantic import Field

    from aoa.action_machine.domain import (
        AssociationOne,
        BaseCoreEntity,
        BaseDomain,
        BaseEnumEntity,
        BaseSpecEntity,
        Classifier,
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


    class SpecDomain(BaseDomain):
        name = "spec"
        description = "Specialization"
    """
)


def _run(body: str) -> str:
    result = run_isolated_model(_IMPORTS + "\n" + textwrap.dedent(body))
    assert result.returncode == 0, result.stderr
    return result.stdout


def test_a_valid_classified_axis_passes() -> None:
    """A head Specialization and an alternative Generalization form a permitted pair."""
    out = _run(
        """
        @entity(description="Kind", domain=SpecDomain)
        class KindEnumEntity(BaseEnumEntity):
            FIRST = value(code="first", display_name="First")

        @entity(description="Head", domain=SpecDomain)
        class HeadCoreEntity(BaseCoreEntity):
            id: str = Field(description="Identifier")
            pressing: Annotated[
                Specialization[AltSpecEntity, KindEnumEntity],
                Inverse(field_name="record"),
            ] = Field(description="Details")

        @entity(description="Alt", domain=SpecDomain)
        class AltSpecEntity(BaseSpecEntity):
            id: str = Field(description="Identifier")
            record: Annotated[
                Generalization[HeadCoreEntity],
                Classifier(variant=KindEnumEntity.FIRST),
                Inverse(HeadCoreEntity, "pressing"),
            ] = Field(description="Record")

        HeadCoreEntity.model_rebuild()
        AltSpecEntity.model_rebuild()
        validate_entity_role_compatibility([HeadCoreEntity, AltSpecEntity, KindEnumEntity])
        print("ACCEPT")
        """
    )
    assert "ACCEPT" in out


def test_a_generalization_paired_with_an_ordinary_role_is_refused() -> None:
    """A Generalization endpoint whose reverse is an ordinary association is refused."""
    out = _run(
        """
        @entity(description="Head", domain=SpecDomain)
        class HeadCoreEntity(BaseCoreEntity):
            id: str = Field(description="Identifier")
            items: Annotated[AssociationOne[AltCoreEntity], Inverse(field_name="owner")] = Field(
                description="Items"
            )

        @entity(description="Alt", domain=SpecDomain)
        class AltCoreEntity(BaseCoreEntity):
            id: str = Field(description="Identifier")
            owner: Annotated[Generalization[HeadCoreEntity], Inverse(HeadCoreEntity, "items")] = Field(
                description="Owner"
            )

        HeadCoreEntity.model_rebuild()
        AltCoreEntity.model_rebuild()
        try:
            validate_entity_role_compatibility([HeadCoreEntity, AltCoreEntity])
            print("ACCEPT")
        except RoleCompatibilityError as exc:
            print("REFUSE " + exc.rule)
        """
    )
    assert "REFUSE Specialization and Generalization pair exclusively" in out


def test_a_specialization_paired_with_an_ordinary_role_is_refused() -> None:
    """A head Specialization whose alternative reverse is an ordinary role is refused."""
    out = _run(
        """
        @entity(description="Kind", domain=SpecDomain)
        class KindEnumEntity(BaseEnumEntity):
            FIRST = value(code="first", display_name="First")

        @entity(description="Head", domain=SpecDomain)
        class HeadCoreEntity(BaseCoreEntity):
            id: str = Field(description="Identifier")
            pressing: Annotated[
                Specialization[AltCoreEntity, KindEnumEntity],
                Inverse(field_name="record"),
            ] = Field(description="Details")

        @entity(description="Alt", domain=SpecDomain)
        class AltCoreEntity(BaseCoreEntity):
            id: str = Field(description="Identifier")
            record: Annotated[AssociationOne[HeadCoreEntity], Inverse(HeadCoreEntity, "pressing")] = Field(
                description="Record"
            )

        HeadCoreEntity.model_rebuild()
        AltCoreEntity.model_rebuild()
        try:
            validate_entity_role_compatibility([HeadCoreEntity, AltCoreEntity, KindEnumEntity])
            print("ACCEPT")
        except RoleCompatibilityError as exc:
            print("REFUSE " + exc.rule)
        """
    )
    assert "REFUSE Specialization and Generalization pair exclusively" in out


def test_spec_spec_and_gen_gen_are_refused_by_the_matrix() -> None:
    """Same-role spec/gen pairs are prohibited at the matrix level."""
    assert roles_compatible("Specialization", "Specialization") is False
    assert roles_compatible("Generalization", "Generalization") is False
