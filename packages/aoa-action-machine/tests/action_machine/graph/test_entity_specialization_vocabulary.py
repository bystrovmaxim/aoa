# tests/action_machine/graph/test_entity_specialization_vocabulary.py
# ruff: noqa: F821  # the class-name alias is the declaration surface
"""
The build rules an axis classified by a closed dictionary must satisfy.

An axis is classified by a dictionary when the head's container names it as the
second type argument. The dictionary must be a decorated, non-empty dictionary;
every alternative must name one of its values, as that value and not a copy of it;
and a head may not name both a dictionary and the earlier `Classifier` marker.
"""

from __future__ import annotations

from typing import Annotated, Literal

import pytest
from pydantic import Field

from aoa.action_machine.domain import (
    BaseCoreEntity,
    BaseDomain,
    BaseEnumEntity,
    BaseSpecEntity,
    Classifier,
    Generalization,
    Rel,
    Specialization,
)
from aoa.action_machine.domain.exceptions import SpecializationDeclarationError
from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
from aoa.action_machine.graph.validators.entity_specialization_validator import (
    validate_entity_specializations,
)
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.intents.entity.entity_specialization_intent_resolver import (
    gather_entity_specialization_intent_resolvers,
)


class VocabularyDomain(BaseDomain):
    """The domain these fixtures belong to."""

    name = "vocabulary"
    description = "Vocabulary"


@exclude_graph_model
@entity(description="Edition kind", domain=VocabularyDomain)
class VocabularyKindEnumEntity(BaseEnumEntity):
    """The dictionary the good axis borrows its codes from."""

    note: str = Field(default="", description="Free note")

    FIRST = VocabularyKindEnumEntity(code="first", display_name="First press")
    REPRESS = VocabularyKindEnumEntity(code="repress", display_name="Repress")


@exclude_graph_model
class EmptyKindEnumEntity(BaseEnumEntity):
    """A base dictionary that declares nothing, so no axis can borrow from it."""


@exclude_graph_model
@entity(description="Other kind", domain=VocabularyDomain)
class OtherKindEnumEntity(BaseEnumEntity):
    """A second dictionary, whose values do not belong to the first."""

    EXTRA = OtherKindEnumEntity(code="extra", display_name="Extra")


@exclude_graph_model
@entity(description="Good head", domain=VocabularyDomain)
class VocabularyGoodHeadCoreEntity(BaseCoreEntity):
    """An axis classified by the dictionary."""

    id: str = Field(description="Head id")
    kind: Specialization[VocabularyFirstSpecEntity | VocabularyRepressSpecEntity, VocabularyKindEnumEntity] = Rel(
        description="Which pressing this is"
    )


@exclude_graph_model
@entity(description="First press", domain=VocabularyDomain)
class VocabularyFirstSpecEntity(BaseSpecEntity):
    """Names the first value."""

    record: Annotated[
        Generalization[VocabularyGoodHeadCoreEntity],
        Classifier(field="record", variant=VocabularyKindEnumEntity.FIRST),
    ] = Rel(description="The head row")


@exclude_graph_model
@entity(description="Repress", domain=VocabularyDomain)
class VocabularyRepressSpecEntity(BaseSpecEntity):
    """Names the second value."""

    record: Annotated[
        Generalization[VocabularyGoodHeadCoreEntity],
        Classifier(field="record", variant=VocabularyKindEnumEntity.REPRESS),
    ] = Rel(description="The head row")



def test_a_dictionary_axis_is_gathered_with_the_dictionary_s_codes() -> None:
    """The resolver reads the codes from the dictionary, and there is no classifier field."""
    axes = gather_entity_specialization_intent_resolvers(VocabularyGoodHeadCoreEntity)

    assert len(axes) == 1
    axis = axes[0]
    assert axis.dictionary is VocabularyKindEnumEntity
    assert axis.codes == ("first", "repress")
    assert axis.classifier_field == ""


def test_a_dictionary_axis_passes_the_rules() -> None:
    """The good declaration is accepted, so the rules do not refuse the declared form."""
    validate_entity_specializations(
        [
            VocabularyGoodHeadCoreEntity,
            VocabularyFirstSpecEntity,
            VocabularyRepressSpecEntity,
            VocabularyKindEnumEntity,
        ]
    )


@exclude_graph_model
@entity(description="Empty head", domain=VocabularyDomain)
class VocabularyEmptyHeadCoreEntity(BaseCoreEntity):
    """An axis borrowing from a dictionary that declares nothing."""

    id: str = Field(description="Head id")
    kind: Specialization[VocabularyEmptySpecEntity, EmptyKindEnumEntity] = Rel(description="Empty dictionary")


@exclude_graph_model
@entity(description="Empty extension", domain=VocabularyDomain)
class VocabularyEmptySpecEntity(BaseSpecEntity):
    """Points back at the empty head."""

    record: Annotated[
        Generalization[VocabularyEmptyHeadCoreEntity],
        Classifier(field="record", variant=VocabularyKindEnumEntity.FIRST),
    ] = Rel(description="The head row")


def test_an_axis_cannot_borrow_from_an_empty_dictionary() -> None:
    """A dictionary with no values could name nothing, so the axis is refused."""
    with pytest.raises(SpecializationDeclarationError, match="declares no values"):
        validate_entity_specializations([VocabularyEmptyHeadCoreEntity, VocabularyEmptySpecEntity])


@exclude_graph_model
@entity(description="Wrong head", domain=VocabularyDomain)
class VocabularyWrongHeadCoreEntity(BaseCoreEntity):
    """An axis whose extension names a value of another dictionary."""

    id: str = Field(description="Head id")
    kind: Specialization[VocabularyWrongSpecEntity, VocabularyKindEnumEntity] = Rel(description="Kind")


@exclude_graph_model
@entity(description="Wrong extension", domain=VocabularyDomain)
class VocabularyWrongSpecEntity(BaseSpecEntity):
    """Names a value the head's dictionary does not declare."""

    record: Annotated[
        Generalization[VocabularyWrongHeadCoreEntity],
        Classifier(field="record", variant=OtherKindEnumEntity.EXTRA),
    ] = Rel(description="The head row")


def test_an_extension_must_name_this_dictionary_s_value() -> None:
    """A value of another dictionary is not a value of this one."""
    with pytest.raises(SpecializationDeclarationError, match="does not declare"):
        validate_entity_specializations([VocabularyWrongHeadCoreEntity, VocabularyWrongSpecEntity])


@exclude_graph_model
@entity(description="Copy head", domain=VocabularyDomain)
class VocabularyCopyHeadCoreEntity(BaseCoreEntity):
    """An axis whose extension names a copy of a declared value."""

    id: str = Field(description="Head id")
    kind: Specialization[VocabularyCopySpecEntity, VocabularyKindEnumEntity] = Rel(description="Kind")


@exclude_graph_model
@entity(description="Copy extension", domain=VocabularyDomain)
class VocabularyCopySpecEntity(BaseSpecEntity):
    """Names a constructed copy, which is not the declared object."""

    record: Annotated[
        Generalization[VocabularyCopyHeadCoreEntity],
        Classifier(
            field="record",
            variant=VocabularyKindEnumEntity(code="first", display_name="First press", note="mine"),
        ),
    ] = Rel(description="The head row")


def test_a_copy_of_a_value_is_not_a_value() -> None:
    """Identity is the test: a copy has the same code and is still refused."""
    with pytest.raises(SpecializationDeclarationError, match="does not declare"):
        validate_entity_specializations([VocabularyCopyHeadCoreEntity, VocabularyCopySpecEntity])


@exclude_graph_model
@entity(description="Both head", domain=VocabularyDomain)
class VocabularyBothHeadCoreEntity(BaseCoreEntity):
    """Names a dictionary and the earlier marker at once."""

    id: str = Field(description="Head id")
    kind_code: Literal["first", "repress"] = Field(description="Classifier field")
    kind: Annotated[
        Specialization[VocabularyBothSpecEntity, VocabularyKindEnumEntity],
        Classifier("kind_code", Literal["first", "repress"]),
    ] = Rel(description="Kind")


@exclude_graph_model
@entity(description="Both extension", domain=VocabularyDomain)
class VocabularyBothSpecEntity(BaseSpecEntity):
    """Points back at the head that carries both forms."""

    record: Annotated[
        Generalization[VocabularyBothHeadCoreEntity],
        Classifier(field="record", variant=VocabularyKindEnumEntity.FIRST),
    ] = Rel(description="The head row")


def test_a_head_cannot_name_both_forms() -> None:
    """A head classified by a dictionary has no classifier field, so the marker is a contradiction."""
    with pytest.raises(SpecializationDeclarationError, match="names both a Classifier marker and a closed dictionary"):
        gather_entity_specialization_intent_resolvers(VocabularyBothHeadCoreEntity)


for _fixture in (
    VocabularyKindEnumEntity,
    VocabularyGoodHeadCoreEntity,
    VocabularyFirstSpecEntity,
    VocabularyRepressSpecEntity,
    VocabularyEmptyHeadCoreEntity,
    VocabularyEmptySpecEntity,
    VocabularyWrongHeadCoreEntity,
    VocabularyWrongSpecEntity,
    VocabularyCopyHeadCoreEntity,
    VocabularyCopySpecEntity,
    VocabularyBothHeadCoreEntity,
    VocabularyBothSpecEntity,
):
    _fixture.model_rebuild()
