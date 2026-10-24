# packages/aoa-action-machine/tests/action_machine/graph/test_role_compatibility_diagnostics.py
"""
Diagnostics: exact exception type, text and failure boundary for each refusal family.

A prohibited pair raises ``RoleCompatibilityError`` carrying both endpoints and both roles;
the ownership rule never claims all Many relationships are prohibited, and an earlier
declaration check (a missing marker, a one-sided inverse) still reports its own boundary.
"""

from __future__ import annotations

import textwrap

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
        CompositeMany,
        CompositeOne,
        Generalization,
        Inverse,
        NoInverse,
        Specialization,
        value,
    )
    from aoa.action_machine.domain.exceptions import EntityFieldDeclarationError, RoleCompatibilityError
    from aoa.action_machine.graph.validators.entity_field_validator import validate_entity_fields
    from aoa.action_machine.graph.validators.entity_inverse_validator import validate_entity_inverses
    from aoa.action_machine.graph.validators.entity_role_compatibility_validator import (
        validate_entity_role_compatibility,
    )
    from aoa.action_machine.intents.entity import entity


    class DiagDomain(BaseDomain):
        name = "diag"
        description = "Diagnostics"
    """
)


def _run(body: str) -> str:
    result = run_isolated_model(_IMPORTS + "\n" + textwrap.dedent(body))
    assert result.returncode == 0, result.stderr
    return result.stdout


def test_ownership_refusal_type_attributes_and_text() -> None:
    """An ownership/ownership refusal is a typed error carrying both endpoints and roles."""
    out = _run(
        """
        @entity(description="A", domain=DiagDomain)
        class ACoreEntity(BaseCoreEntity):
            id: str = Field(description="Identifier")
            b: Annotated[CompositeOne[BCoreEntity], Inverse(field_name="a")] = Field(description="B")

        @entity(description="B", domain=DiagDomain)
        class BCoreEntity(BaseCoreEntity):
            id: str = Field(description="Identifier")
            a: Annotated[CompositeMany[ACoreEntity], Inverse(field_name="b")] = Field(description="A")

        ACoreEntity.model_rebuild()
        BCoreEntity.model_rebuild()
        try:
            validate_entity_role_compatibility([ACoreEntity, BCoreEntity])
            print("ACCEPT")
        except RoleCompatibilityError as exc:
            print("TYPE " + type(exc).__name__)
            print("FIRST " + exc.first_entity + " " + exc.first_field + " " + exc.first_role)
            print("SECOND " + exc.second_entity + " " + exc.second_field + " " + exc.second_role)
            print("MESSAGE " + str(exc))
        """
    )

    assert "TYPE RoleCompatibilityError" in out
    assert "FIRST ACoreEntity b CompositeOne" in out
    assert "SECOND BCoreEntity a CompositeMany" in out
    assert "both endpoints carry ownership roles" in out
    assert "AssociationOne or AssociationMany" in out
    assert "change one of these two endpoints" in out
    # It must not claim that all Many relationships are prohibited.
    assert "all Many" not in out
    assert "Many relationships are prohibited" not in out


def test_specialization_ordinary_refusal_names_the_exclusive_pairing() -> None:
    """A specialization/ordinary mismatch says the two roles pair exclusively."""
    out = _run(
        """
        @entity(description="Kind", domain=DiagDomain)
        class KindEnumEntity(BaseEnumEntity):
            FIRST = value(code="first", display_name="First")

        @entity(description="Head", domain=DiagDomain)
        class HeadCoreEntity(BaseCoreEntity):
            id: str = Field(description="Identifier")
            pressing: Annotated[
                Specialization[AltCoreEntity, KindEnumEntity],
                Inverse(field_name="record"),
            ] = Field(description="Details")

        @entity(description="Alt", domain=DiagDomain)
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
            print("TYPE " + type(exc).__name__)
            print("MESSAGE " + str(exc))
        """
    )

    assert "TYPE RoleCompatibilityError" in out
    assert "Specialization and Generalization pair exclusively with each other" in out


def test_a_missing_direction_marker_is_reported_by_the_earlier_pass() -> None:
    """A field with no direction marker is refused by the completeness pass, not the matrix."""
    out = _run(
        """
        @entity(description="A", domain=DiagDomain)
        class ACoreEntity(BaseCoreEntity):
            id: str = Field(description="Identifier")
            b: CompositeOne[BCoreEntity] = Field(description="B")

        @entity(description="B", domain=DiagDomain)
        class BCoreEntity(BaseCoreEntity):
            id: str = Field(description="Identifier")

        ACoreEntity.model_rebuild()
        BCoreEntity.model_rebuild()
        try:
            validate_entity_fields([ACoreEntity, BCoreEntity])
            print("ACCEPT")
        except EntityFieldDeclarationError:
            print("EARLIER EntityFieldDeclarationError")
        except RoleCompatibilityError:
            print("WRONG RoleCompatibilityError")
        """
    )
    assert "EARLIER EntityFieldDeclarationError" in out
    assert "WRONG" not in out


def test_a_one_sided_inverse_is_reported_by_the_inverse_pass() -> None:
    """An Inverse paired with a NoInverse endpoint is refused by the inverse pass first."""
    out = _run(
        """
        @entity(description="A", domain=DiagDomain)
        class ACoreEntity(BaseCoreEntity):
            id: str = Field(description="Identifier")
            b: Annotated[CompositeOne[BCoreEntity], NoInverse()] = Field(description="B")

        @entity(description="B", domain=DiagDomain)
        class BCoreEntity(BaseCoreEntity):
            id: str = Field(description="Identifier")
            a: Annotated[CompositeMany[ACoreEntity], Inverse(field_name="b")] = Field(description="A")

        ACoreEntity.model_rebuild()
        BCoreEntity.model_rebuild()
        try:
            validate_entity_inverses([ACoreEntity, BCoreEntity])
            print("ACCEPT")
        except EntityFieldDeclarationError:
            print("EARLIER EntityFieldDeclarationError")
        except RoleCompatibilityError:
            print("WRONG RoleCompatibilityError")
        """
    )
    assert "EARLIER EntityFieldDeclarationError" in out
    assert "WRONG" not in out
