# packages/aoa-action-machine/tests/action_machine/graph/test_role_compatibility_noinverse.py
"""
The NoInverse table: unpaired, reciprocal, refused, independent, and forbidden on spec/gen.

``NoInverse`` is permitted on each of the six ordinary containers and means the field has no
reverse endpoint. It is refused when an ``Inverse`` targets it, and on ``Specialization`` and
``Generalization``, which require a reciprocal ``Inverse`` pair. Two opposite-direction
``NoInverse`` fields are two independent relationships, never a reciprocal pair.
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
    from aoa.action_machine.domain.exceptions import (
        EntityFieldDeclarationError,
        RoleCompatibilityError,
        SpecializationDeclarationError,
    )
    from aoa.action_machine.graph.validators.entity_field_validator import validate_entity_fields
    from aoa.action_machine.graph.validators.entity_inverse_validator import validate_entity_inverses
    from aoa.action_machine.graph.validators.entity_role_compatibility_validator import (
        validate_entity_role_compatibility,
    )
    from aoa.action_machine.graph.validators.entity_specialization_validator import (
        validate_entity_specializations,
    )
    from aoa.action_machine.intents.entity import entity


    class NoInvDomain(BaseDomain):
        name = "noinv"
        description = "NoInverse"
    """
)


def _run(body: str) -> str:
    result = run_isolated_model(_IMPORTS + "\n" + textwrap.dedent(body))
    assert result.returncode == 0, result.stderr
    return result.stdout


_CONTAINERS = [
    "AssociationOne",
    "AssociationMany",
    "AggregateOne",
    "AggregateMany",
    "CompositeOne",
    "CompositeMany",
]


@pytest.mark.parametrize("container", _CONTAINERS)
def test_noinverse_is_accepted_on_each_ordinary_container(container: str) -> None:
    """A one-way field is accepted on all six ordinary containers."""
    out = _run(
        f"""
        @entity(description="Owner", domain=NoInvDomain)
        class OwnerCoreEntity(BaseCoreEntity):
            id: str = Field(description="Identifier")
            parts: Annotated[{container}[PartCoreEntity], NoInverse()] = Field(description="Parts")

        @entity(description="Part", domain=NoInvDomain)
        class PartCoreEntity(BaseCoreEntity):
            id: str = Field(description="Identifier")

        OwnerCoreEntity.model_rebuild()
        PartCoreEntity.model_rebuild()
        validate_entity_fields([OwnerCoreEntity, PartCoreEntity])
        validate_entity_inverses([OwnerCoreEntity, PartCoreEntity])
        print("ACCEPT")
        """
    )
    assert "ACCEPT" in out, out


def test_one_unpaired_noinverse_field_is_accepted() -> None:
    """A single NoInverse field with no reverse field is a valid one-way relationship."""
    out = _run(
        """
        @entity(description="Owner", domain=NoInvDomain)
        class OwnerCoreEntity(BaseCoreEntity):
            id: str = Field(description="Identifier")
            part: Annotated[AssociationOne[PartCoreEntity], NoInverse()] = Field(description="Part")

        @entity(description="Part", domain=NoInvDomain)
        class PartCoreEntity(BaseCoreEntity):
            id: str = Field(description="Identifier")

        OwnerCoreEntity.model_rebuild()
        PartCoreEntity.model_rebuild()
        validate_entity_inverses([OwnerCoreEntity, PartCoreEntity])
        print("ACCEPT")
        """
    )
    assert "ACCEPT" in out


def test_two_noinverse_fields_are_independent() -> None:
    """Two opposite-direction NoInverse fields are two relationships, not one pair."""
    out = _run(
        """
        @entity(description="A", domain=NoInvDomain)
        class ACoreEntity(BaseCoreEntity):
            id: str = Field(description="Identifier")
            b: Annotated[AssociationOne[BCoreEntity], NoInverse()] = Field(description="B")

        @entity(description="B", domain=NoInvDomain)
        class BCoreEntity(BaseCoreEntity):
            id: str = Field(description="Identifier")
            a: Annotated[AssociationMany[ACoreEntity], NoInverse()] = Field(description="A")

        ACoreEntity.model_rebuild()
        BCoreEntity.model_rebuild()
        validate_entity_inverses([ACoreEntity, BCoreEntity])
        validate_entity_role_compatibility([ACoreEntity, BCoreEntity])
        print("ACCEPT")
        """
    )
    assert "ACCEPT" in out


def test_two_mutual_inverse_markers_are_accepted() -> None:
    """A reciprocal pair of Inverse markers is accepted and passes the matrix."""
    out = _run(
        """
        @entity(description="A", domain=NoInvDomain)
        class ACoreEntity(BaseCoreEntity):
            id: str = Field(description="Identifier")
            b: Annotated[AssociationOne[BCoreEntity], Inverse(field_name="a")] = Field(description="B")

        @entity(description="B", domain=NoInvDomain)
        class BCoreEntity(BaseCoreEntity):
            id: str = Field(description="Identifier")
            a: Annotated[AssociationMany[ACoreEntity], Inverse(field_name="b")] = Field(description="A")

        ACoreEntity.model_rebuild()
        BCoreEntity.model_rebuild()
        validate_entity_inverses([ACoreEntity, BCoreEntity])
        validate_entity_role_compatibility([ACoreEntity, BCoreEntity])
        print("ACCEPT")
        """
    )
    assert "ACCEPT" in out


def _one_sided(order: tuple[str, str]) -> str:
    """Return the verdict for an Inverse targeting a NoInverse field, in the given order."""
    first, second = order
    return _run(
        f"""
        @entity(description="Owner", domain=NoInvDomain)
        class OwnerCoreEntity(BaseCoreEntity):
            id: str = Field(description="Identifier")
            part: Annotated[AssociationMany[PartCoreEntity], NoInverse()] = Field(description="Part")

        @entity(description="Part", domain=NoInvDomain)
        class PartCoreEntity(BaseCoreEntity):
            id: str = Field(description="Identifier")
            owner: Annotated[AssociationOne[OwnerCoreEntity], Inverse(field_name="part")] = Field(
                description="Owner"
            )

        OwnerCoreEntity.model_rebuild()
        PartCoreEntity.model_rebuild()
        try:
            validate_entity_inverses([{first}, {second}])
            print("ACCEPT")
        except EntityFieldDeclarationError:
            print("REFUSE")
        """
    )


def test_an_inverse_targeting_a_noinverse_field_is_refused_either_order() -> None:
    """A paired field cannot use an unpaired NoInverse field as its reverse endpoint."""
    assert "REFUSE" in _one_sided(("OwnerCoreEntity", "PartCoreEntity"))
    assert "REFUSE" in _one_sided(("PartCoreEntity", "OwnerCoreEntity"))


def test_noinverse_on_specialization_is_refused() -> None:
    """A head field marked NoInverse is refused; the pair requires Inverse."""
    out = _run(
        """
        @entity(description="Kind", domain=NoInvDomain)
        class KindEnumEntity(BaseEnumEntity):
            FIRST = value(code="first", display_name="First")

        @entity(description="Head", domain=NoInvDomain)
        class HeadCoreEntity(BaseCoreEntity):
            id: str = Field(description="Identifier")
            pressing: Annotated[Specialization[AltSpecEntity, KindEnumEntity], NoInverse()] = Field(
                description="Details"
            )

        @entity(description="Alt", domain=NoInvDomain)
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
            validate_entity_specializations()
            print("ACCEPT")
        except SpecializationDeclarationError:
            print("REFUSE")
        """
    )
    assert "REFUSE" in out


def test_noinverse_on_generalization_is_refused() -> None:
    """An alternative field marked NoInverse is refused; the pair requires Inverse."""
    out = _run(
        """
        @entity(description="Kind", domain=NoInvDomain)
        class KindEnumEntity(BaseEnumEntity):
            FIRST = value(code="first", display_name="First")

        @entity(description="Head", domain=NoInvDomain)
        class HeadCoreEntity(BaseCoreEntity):
            id: str = Field(description="Identifier")
            pressing: Annotated[
                Specialization[AltSpecEntity, KindEnumEntity],
                Inverse(field_name="record"),
            ] = Field(description="Details")

        @entity(description="Alt", domain=NoInvDomain)
        class AltSpecEntity(BaseSpecEntity):
            id: str = Field(description="Identifier")
            record: Annotated[
                Generalization[HeadCoreEntity],
                Classifier(variant=KindEnumEntity.FIRST),
                NoInverse(),
            ] = Field(description="Record")

        HeadCoreEntity.model_rebuild()
        AltSpecEntity.model_rebuild()
        try:
            validate_entity_specializations()
            print("ACCEPT")
        except SpecializationDeclarationError:
            print("REFUSE")
        """
    )
    assert "REFUSE" in out
