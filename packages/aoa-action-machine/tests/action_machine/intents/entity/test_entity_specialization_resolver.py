# tests/action_machine/intents/entity/test_entity_specialization_resolver.py
"""
Tests for ``EntitySpecializationIntentResolver`` — reading an axis off a head class.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A head field parameterises ``Specialization[A | B | C]`` and carries a
``Classifier(field=…, codes=Literal[…])`` marker. These tests assert what the parser
reads out of that, and — the part everything else consumes — the mapping from a code
to the class it selects, gathered from each extension's own reverse field.

They also pin the **two-sided comparison** the build will make: every class in the
union must declare exactly one code, and every code the head names must belong to a
class. The parser gathers what it can and leaves the verdict to the build, so these
tests assert both halves — what the mapping holds, and what it is missing.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- **SpecializationDeclarationError** — a ``Specialization`` container without a
  ``Classifier``, or an alternative declaring more than one code on its reverse field.

Does not cover the graph, the rules decided across several heads, or the runtime value.
"""

from __future__ import annotations

from typing import Annotated, Literal

import pytest
from pydantic import Field

from aoa.action_machine.domain import (
    BaseAssocEntity,
    BaseCoreEntity,
    BaseEntity,
    BaseSpecEntity,
    Classifier,
    Generalization,
    Inverse,
    NoGraphEdge,
    Rel,
    Specialization,
)
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.domain.exceptions import SpecializationDeclarationError
from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.intents.entity.entity_intent_resolver import EntityIntentResolver
from aoa.action_machine.intents.entity.entity_specialization_intent_resolver import (
    EntitySpecializationIntentResolver,
    gather_entity_specialization_intent_resolvers,
    is_specialization_field,
)


class _SDomain(BaseDomain):
    name = "s"
    description = "s"


def _code_of(cls: type[BaseEntity]) -> str | None:
    """Return the single code ``cls`` declares on its reverse field, or ``None``."""
    for info in cls.model_fields.values():
        marker = next((item for item in info.metadata if isinstance(item, Classifier)), None)
        if marker is not None and len(marker.code_values) == 1:
            return marker.code_values[0]
    return None


# ─────────────────────────────────────────────────────────────────────────────
# A good axis: three alternatives, three codes, one classifier
# ─────────────────────────────────────────────────────────────────────────────


@exclude_graph_model
@entity(description="First", domain=_SDomain)
class _FirstSpecEntity(BaseSpecEntity):
    id: str = Field(description="id")
    record: Annotated[
        Generalization[_HeadCoreEntity],
        Classifier("record", Literal["first"]),
        Inverse(_HeadCoreEntity, "pressed"),
    ] = Rel(description="back")


@exclude_graph_model
@entity(description="Second", domain=_SDomain)
class _SecondSpecEntity(BaseSpecEntity):
    id: str = Field(description="id")
    record: Annotated[
        Generalization[_HeadCoreEntity],
        Classifier("record", Literal["repress"]),
        Inverse(_HeadCoreEntity, "pressed"),
    ] = Rel(description="back")


@exclude_graph_model
@entity(description="Third", domain=_SDomain)
class _ThirdSpecEntity(BaseSpecEntity):
    id: str = Field(description="id")
    record: Annotated[
        Generalization[_HeadCoreEntity],
        Classifier("record", Literal["test"]),
        Inverse(_HeadCoreEntity, "pressed"),
    ] = Rel(description="back")


@exclude_graph_model
@entity(description="Head", domain=_SDomain)
class _HeadCoreEntity(BaseCoreEntity):
    id: str = Field(description="id")
    media: str = Field(description="classifier")
    pressed: Annotated[
        Specialization[_FirstSpecEntity | _SecondSpecEntity | _ThirdSpecEntity],
        Classifier(field="media", codes=Literal["first", "repress", "test"]),
        Inverse(field_name="record"),
    ] = Rel(description="how it was pressed")


for _cls in (_FirstSpecEntity, _SecondSpecEntity, _ThirdSpecEntity, _HeadCoreEntity):
    _cls.model_rebuild()


# ─────────────────────────────────────────────────────────────────────────────
# A head over a class that declares no code
# ─────────────────────────────────────────────────────────────────────────────


@exclude_graph_model
@entity(description="Silent", domain=_SDomain)
class _SilentSpecEntity(BaseSpecEntity):
    id: str = Field(description="id")
    record: Annotated[Generalization[_HeadWithSilentCoreEntity], Inverse(_HeadWithSilentCoreEntity, "pressed")] = Rel(
        description="back, with no code"
    )


@exclude_graph_model
@entity(description="First for silent", domain=_SDomain)
class _FirstForSilentSpecEntity(BaseSpecEntity):
    id: str = Field(description="id")
    record: Annotated[
        Generalization[_HeadWithSilentCoreEntity],
        Classifier("record", Literal["first"]),
        Inverse(_HeadWithSilentCoreEntity, "pressed"),
    ] = Rel(description="back")


@exclude_graph_model
@entity(description="Head over a silent class", domain=_SDomain)
class _HeadWithSilentCoreEntity(BaseCoreEntity):
    id: str = Field(description="id")
    media: str = Field(description="classifier")
    pressed: Annotated[
        Specialization[_FirstForSilentSpecEntity | _SilentSpecEntity],
        Classifier(field="media", codes=Literal["first", "repress"]),
        Inverse(field_name="record"),
    ] = Rel(description="one class declares nothing")


# ─────────────────────────────────────────────────────────────────────────────
# A head over a class that declares two codes
# ─────────────────────────────────────────────────────────────────────────────


@exclude_graph_model
@entity(description="Greedy", domain=_SDomain)
class _GreedySpecEntity(BaseSpecEntity):
    id: str = Field(description="id")
    record: Annotated[
        Generalization[_HeadWithGreedyCoreEntity],
        Classifier("record", Literal["first", "repress"]),
        Inverse(_HeadWithGreedyCoreEntity, "pressed"),
    ] = Rel(description="back, with two codes")


@exclude_graph_model
@entity(description="Head over a greedy class", domain=_SDomain)
class _HeadWithGreedyCoreEntity(BaseCoreEntity):
    id: str = Field(description="id")
    media: str = Field(description="classifier")
    pressed: Annotated[
        Specialization[_GreedySpecEntity],
        Classifier(field="media", codes=Literal["first"]),
        Inverse(field_name="record"),
    ] = Rel(description="one class declares two codes")


# ─────────────────────────────────────────────────────────────────────────────
# A head whose two classes answer to one code
# ─────────────────────────────────────────────────────────────────────────────


@exclude_graph_model
@entity(description="Twin A", domain=_SDomain)
class _TwinASpecEntity(BaseSpecEntity):
    id: str = Field(description="id")
    record: Annotated[
        Generalization[_HeadWithTwinCoreEntity],
        Classifier("record", Literal["first"]),
        Inverse(_HeadWithTwinCoreEntity, "pressed"),
    ] = Rel(description="back")


@exclude_graph_model
@entity(description="Twin B", domain=_SDomain)
class _TwinBSpecEntity(BaseSpecEntity):
    id: str = Field(description="id")
    record: Annotated[
        Generalization[_HeadWithTwinCoreEntity],
        Classifier("record", Literal["first"]),
        Inverse(_HeadWithTwinCoreEntity, "pressed"),
    ] = Rel(description="back, with the same code")


@exclude_graph_model
@entity(description="Head over twins", domain=_SDomain)
class _HeadWithTwinCoreEntity(BaseCoreEntity):
    id: str = Field(description="id")
    media: str = Field(description="classifier")
    pressed: Annotated[
        Specialization[_TwinASpecEntity | _TwinBSpecEntity],
        Classifier(field="media", codes=Literal["first", "repress"]),
        Inverse(field_name="record"),
    ] = Rel(description="two classes answer to one code")


# ─────────────────────────────────────────────────────────────────────────────
# What is not an axis: a plain column, a bare container, a quiet axis
# ─────────────────────────────────────────────────────────────────────────────


@exclude_graph_model
@entity(description="Plain", domain=_SDomain)
class _PlainCoreEntity(BaseCoreEntity):
    id: str = Field(description="id")
    note: str = Field(description="an ordinary column")


@exclude_graph_model
@entity(description="Bare container", domain=_SDomain)
class _BareContainerAssocEntity(BaseAssocEntity):
    id: str = Field(description="id")
    pressed: Annotated[Specialization[_FirstSpecEntity], Inverse(field_name="record")] = Rel(description="no marker")


@exclude_graph_model
@entity(description="Quiet head", domain=_SDomain)
class _QuietHeadCoreEntity(BaseCoreEntity):
    id: str = Field(description="id")
    media: str = Field(description="classifier")
    pressed: Annotated[
        Specialization[_FirstSpecEntity],
        Classifier(field="media", codes=Literal["first"]),
        NoGraphEdge(),
        Inverse(field_name="record"),
    ] = Rel(description="kept out of the graph")


for _cls in (
    _SilentSpecEntity,
    _FirstForSilentSpecEntity,
    _HeadWithSilentCoreEntity,
    _GreedySpecEntity,
    _HeadWithGreedyCoreEntity,
    _TwinASpecEntity,
    _TwinBSpecEntity,
    _HeadWithTwinCoreEntity,
    _PlainCoreEntity,
    _BareContainerAssocEntity,
    _QuietHeadCoreEntity,
):
    _cls.model_rebuild()


def _axis(cls: type[BaseEntity] = _HeadCoreEntity) -> EntitySpecializationIntentResolver:
    """Return the single axis declared on ``cls``."""
    axes = gather_entity_specialization_intent_resolvers(cls)
    assert len(axes) == 1
    return axes[0]


# ─────────────────────────────────────────────────────────────────────────────
# Reading a good axis
# ─────────────────────────────────────────────────────────────────────────────


def test_an_axis_is_read_with_its_classes_codes_and_classifier() -> None:
    axis = _axis()

    assert axis.field_name == "pressed"
    assert axis.head_entity is _HeadCoreEntity
    assert axis.classifier_field == "media"
    assert axis.alternatives == (_FirstSpecEntity, _SecondSpecEntity, _ThirdSpecEntity)
    assert axis.codes == ("first", "repress", "test")
    assert axis.inverse_field == "record"
    assert axis.description == "how it was pressed"
    assert axis.omit_graph_edge is False


def test_declaration_order_is_preserved() -> None:
    axis = _axis()
    assert [cls.__name__ for cls in axis.alternatives] == ["_FirstSpecEntity", "_SecondSpecEntity", "_ThirdSpecEntity"]
    assert list(axis.codes) == ["first", "repress", "test"]


def test_the_mapping_pairs_each_class_with_the_code_it_declares() -> None:
    axis = _axis()
    assert axis.code_to_target == {
        "first": _FirstSpecEntity,
        "repress": _SecondSpecEntity,
        "test": _ThirdSpecEntity,
    }


def test_the_facade_returns_what_the_parser_returns() -> None:
    assert EntityIntentResolver.resolve_entity_specializations(
        _HeadCoreEntity
    ) == gather_entity_specialization_intent_resolvers(_HeadCoreEntity)


# ─────────────────────────────────────────────────────────────────────────────
# The two-sided comparison
# ─────────────────────────────────────────────────────────────────────────────


def test_both_sides_agree_on_a_good_model() -> None:
    axis = _axis()

    assert {_code_of(cls) for cls in axis.alternatives} == set(axis.codes)
    assert len(axis.alternatives) == len(axis.codes)
    assert set(axis.code_to_target) == set(axis.codes)
    assert set(axis.code_to_target.values()) == set(axis.alternatives)


def test_a_class_that_declares_no_code_leaves_the_mapping_short() -> None:
    axis = _axis(_HeadWithSilentCoreEntity)

    assert axis.codes == ("first", "repress")
    assert set(axis.code_to_target) == {"first"}
    assert _SilentSpecEntity not in axis.code_to_target.values()
    assert len(axis.code_to_target) < len(axis.codes)
    assert _code_of(_SilentSpecEntity) is None


def test_a_class_that_declares_two_codes_is_refused_where_its_code_is_read() -> None:
    with pytest.raises(SpecializationDeclarationError, match="must declare exactly one code"):
        _axis(_HeadWithGreedyCoreEntity)


def test_a_repeated_code_leaves_two_classes_on_one_code() -> None:
    axis = _axis(_HeadWithTwinCoreEntity)

    assert axis.codes == ("first", "repress")
    assert _code_of(_TwinASpecEntity) == _code_of(_TwinBSpecEntity) == "first"
    assert len(axis.code_to_target) == 1, "one code, two classes: the head names a code no class owns alone"


# ─────────────────────────────────────────────────────────────────────────────
# What is not an axis
# ─────────────────────────────────────────────────────────────────────────────


def test_a_plain_scalar_field_is_not_an_axis() -> None:
    assert is_specialization_field(str) is False
    assert gather_entity_specialization_intent_resolvers(_PlainCoreEntity) == []


def test_a_marker_without_a_container_is_not_an_axis() -> None:
    """An extension's reverse field carries a `Classifier` too, and is not an axis."""
    assert gather_entity_specialization_intent_resolvers(_FirstSpecEntity) == []


def test_a_container_without_a_marker_is_refused() -> None:
    with pytest.raises(SpecializationDeclarationError, match="neither a Classifier marker nor a closed dictionary"):
        gather_entity_specialization_intent_resolvers(_BareContainerAssocEntity)


def test_no_graph_edge_is_carried_onto_the_axis() -> None:
    assert _axis(_QuietHeadCoreEntity).omit_graph_edge is True


def test_a_class_with_no_axis_returns_an_empty_list() -> None:
    assert gather_entity_specialization_intent_resolvers(_SDomain) == []
