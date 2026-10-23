# tests/action_machine/graph/test_entity_specialization_vocabulary.py
"""
The build rules an axis classified by a closed dictionary must satisfy.

An axis is classified by a dictionary when the head's container names it as the
second type argument. The dictionary must be a decorated, non-empty dictionary;
every alternative must name one of its values, as that value and not a copy of it;
and a head may not name both a dictionary and the earlier `Classifier` marker.
"""

from __future__ import annotations

from typing import Annotated

import pytest
from pydantic import Field

from aoa.action_machine.domain import (
    BaseCoreEntity,
    BaseDomain,
    BaseEnumEntity,
    BaseSpecEntity,
    Classifier,
    Generalization,
    Specialization,
    value,
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

    FIRST = value(code="first", display_name="First press")
    REPRESS = value(code="repress", display_name="Repress")


@exclude_graph_model
class EmptyKindEnumEntity(BaseEnumEntity):
    """A base dictionary that declares nothing, so no axis can borrow from it."""


@exclude_graph_model
@entity(description="Other kind", domain=VocabularyDomain)
class OtherKindEnumEntity(BaseEnumEntity):
    """A second dictionary, whose values do not belong to the first."""

    EXTRA = value(code="extra", display_name="Extra")


@exclude_graph_model
@entity(description="Good head", domain=VocabularyDomain)
class VocabularyGoodHeadCoreEntity(BaseCoreEntity):
    """An axis classified by the dictionary."""

    id: str = Field(description="Head id")
    kind: Specialization[VocabularyFirstSpecEntity | VocabularyRepressSpecEntity, VocabularyKindEnumEntity] = Field(
        description="Which pressing this is"
    )


@exclude_graph_model
@entity(description="First press", domain=VocabularyDomain)
class VocabularyFirstSpecEntity(BaseSpecEntity):
    """Names the first value."""

    record: Annotated[
        Generalization[VocabularyGoodHeadCoreEntity],
        Classifier(variant=VocabularyKindEnumEntity.FIRST),
    ] = Field(description="The head row")


@exclude_graph_model
@entity(description="Repress", domain=VocabularyDomain)
class VocabularyRepressSpecEntity(BaseSpecEntity):
    """Names the second value."""

    record: Annotated[
        Generalization[VocabularyGoodHeadCoreEntity],
        Classifier(variant=VocabularyKindEnumEntity.REPRESS),
    ] = Field(description="The head row")



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
    kind: Specialization[VocabularyEmptySpecEntity, EmptyKindEnumEntity] = Field(description="Empty dictionary")


@exclude_graph_model
@entity(description="Empty extension", domain=VocabularyDomain)
class VocabularyEmptySpecEntity(BaseSpecEntity):
    """Points back at the empty head."""

    record: Annotated[
        Generalization[VocabularyEmptyHeadCoreEntity],
        Classifier(variant=VocabularyKindEnumEntity.FIRST),
    ] = Field(description="The head row")


def test_an_axis_cannot_borrow_from_an_empty_dictionary() -> None:
    """A dictionary with no values could name nothing, so the axis is refused."""
    with pytest.raises(SpecializationDeclarationError, match="declares no values"):
        validate_entity_specializations([VocabularyEmptyHeadCoreEntity, VocabularyEmptySpecEntity])


@exclude_graph_model
@entity(description="Wrong head", domain=VocabularyDomain)
class VocabularyWrongHeadCoreEntity(BaseCoreEntity):
    """An axis whose extension names a value of another dictionary."""

    id: str = Field(description="Head id")
    kind: Specialization[VocabularyWrongSpecEntity, VocabularyKindEnumEntity] = Field(description="Kind")


@exclude_graph_model
@entity(description="Wrong extension", domain=VocabularyDomain)
class VocabularyWrongSpecEntity(BaseSpecEntity):
    """Names a value the head's dictionary does not declare."""

    record: Annotated[
        Generalization[VocabularyWrongHeadCoreEntity],
        Classifier(variant=OtherKindEnumEntity.EXTRA),
    ] = Field(description="The head row")


def test_an_extension_must_name_this_dictionary_s_value() -> None:
    """A value of another dictionary is not a value of this one."""
    with pytest.raises(SpecializationDeclarationError, match="does not declare"):
        validate_entity_specializations([VocabularyWrongHeadCoreEntity, VocabularyWrongSpecEntity])


@exclude_graph_model
@entity(description="Copy head", domain=VocabularyDomain)
class VocabularyCopyHeadCoreEntity(BaseCoreEntity):
    """An axis whose extension names a copy of a declared value."""

    id: str = Field(description="Head id")
    kind: Specialization[VocabularyCopySpecEntity, VocabularyKindEnumEntity] = Field(description="Kind")


@exclude_graph_model
@entity(description="Copy extension", domain=VocabularyDomain)
class VocabularyCopySpecEntity(BaseSpecEntity):
    """Names a constructed copy, which is not the declared object."""

    record: Annotated[
        Generalization[VocabularyCopyHeadCoreEntity],
        Classifier(
            variant=VocabularyKindEnumEntity(code="first", display_name="First press", note="mine"),
        ),
    ] = Field(description="The head row")


def test_a_copy_of_a_value_is_not_a_value() -> None:
    """Identity is the test: a copy has the same code and is still refused."""
    with pytest.raises(SpecializationDeclarationError, match="does not declare"):
        validate_entity_specializations([VocabularyCopyHeadCoreEntity, VocabularyCopySpecEntity])


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
):
    _fixture.model_rebuild()


def test_a_head_side_classifier_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    """The dictionary is the head's only classification declaration."""
    info = VocabularyGoodHeadCoreEntity.model_fields["kind"]
    monkeypatch.setattr(info, "metadata", [
        *info.metadata, Classifier(variant=VocabularyKindEnumEntity.FIRST),
    ])
    with pytest.raises(SpecializationDeclarationError, match=r"head.*Classifier"):
        validate_entity_specializations([
            VocabularyGoodHeadCoreEntity, VocabularyFirstSpecEntity, VocabularyRepressSpecEntity,
        ])


def test_a_classifier_cannot_name_a_field_any_more() -> None:
    """The marker names a value only: the attribute it sits on is the pair, so the name is gone."""
    with pytest.raises(TypeError, match="field"):
        Classifier(field="record", variant=VocabularyKindEnumEntity.FIRST)


def test_an_optional_axis_keeps_its_dictionary_and_graph_edges() -> None:
    """Absence of a value must not hide the declared axis from the graph."""
    from aoa.action_machine.graph.edges.entity_specialization_graph_edge import EntitySpecializationGraphEdge

    @exclude_graph_model
    @entity(description="Optional kind", domain=VocabularyDomain)
    class OptionalKindEnumEntity(BaseEnumEntity):
        """Declare the one possible classification."""
        FIRST = value(code="first", display_name="First")

    @exclude_graph_model
    @entity(description="Optional head", domain=VocabularyDomain)
    class OptionalHeadCoreEntity(BaseCoreEntity):
        """Allow a head whose classification has not been supplied."""
        kind: Specialization[OptionalDetailsSpecEntity, OptionalKindEnumEntity] | None = Field(description="Optional choice")

    @exclude_graph_model
    @entity(description="Optional details", domain=VocabularyDomain)
    class OptionalDetailsSpecEntity(BaseSpecEntity):
        """Describe the classified head."""
        record: Annotated[
            Generalization[OptionalHeadCoreEntity],
            Classifier(variant=OptionalKindEnumEntity.FIRST),
        ] = Field(description="Head")

    OptionalHeadCoreEntity.model_rebuild(_types_namespace=locals())
    OptionalDetailsSpecEntity.model_rebuild(_types_namespace=locals())
    axes = gather_entity_specialization_intent_resolvers(OptionalHeadCoreEntity)
    assert len(axes) == 1
    assert axes[0].dictionary is OptionalKindEnumEntity
    validate_entity_specializations([OptionalHeadCoreEntity, OptionalDetailsSpecEntity])
    assert len(EntitySpecializationGraphEdge.get_entity_specialization_edges(OptionalHeadCoreEntity)) == 1
    assert OptionalHeadCoreEntity(kind=None).kind is None
