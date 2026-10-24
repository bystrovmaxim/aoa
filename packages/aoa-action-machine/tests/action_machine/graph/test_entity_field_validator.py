# tests/action_machine/graph/test_entity_field_validator.py
"""
Tests for ``validate_entity_fields`` — every entity field must declare a complete relationship.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A Core, Assoc, Detail, Spec or Enum entity-valued field must declare its relationship
completely: a supported container inside ``Annotated``, exactly one direction marker and a
non-blank assignment-side ``Field(description=...)``. A dictionary field uses
``AssociationOne[D] | None`` with ``NoInverse()``. These tests pin the complete forms and
every incomplete shape across the five stereotypes, plus the retained State/scalar controls.

Every intentionally invalid declaration is created and judged inside a **fresh
interpreter** via ``tests.support.isolated_entity_models.run_isolated_model``. The
completeness rule enumerates every loaded ``@entity`` class, so an invalid fixture left at
module level would poison model assembly for every other test in the same session.
"""

from __future__ import annotations

import textwrap

import pytest

from aoa.action_machine.domain import (
    BaseCoreEntity,
    BaseEnumEntity,
    BaseStateEntity,
    NoRelation,
)
from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
from aoa.action_machine.graph.validators.entity_field_validator import _kind_of
from aoa.action_machine.graph.validators.entity_specialization_validator import declared_entity_classes

from ...support.isolated_entity_models import run_isolated_model

# ─────────────────────────────────────────────────────────────────────────────
# Subprocess preamble — every fixture script shares these imports and helpers.
# ─────────────────────────────────────────────────────────────────────────────

_IMPORTS = textwrap.dedent(
    """
    from collections.abc import Sequence
    from typing import Annotated

    from pydantic import Field, ValidationError

    from aoa.action_machine.domain import (
        AggregateMany,
        AggregateOne,
        AssociationMany,
        AssociationOne,
        BaseAssocEntity,
        BaseCoreEntity,
        BaseDetailEntity,
        BaseDomain,
        BaseEnumEntity,
        BaseSpecEntity,
        BaseStateEntity,
        CompositeMany,
        CompositeOne,
        Generalization,
        Inverse,
        Lifecycle,
        NoGraphEdge,
        NoInverse,
        NoRelation,
        Specialization,
        value,
    )
    from aoa.action_machine.domain.exceptions import EntityFieldDeclarationError
    from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
    from aoa.action_machine.graph.nodes.entity_graph_node import EntityGraphNode
    from aoa.action_machine.graph.validators.entity_field_validator import validate_entity_fields
    from aoa.action_machine.intents.entity import entity
    from aoa.action_machine.model.base_schema import BaseSchema


    def probe(cls):
        \"\"\"Judge one class and print a deterministic result block.\"\"\"
        print("FIXTURE " + cls.__name__)
        try:
            validate_entity_fields([cls])
            print("ACCEPT")
        except EntityFieldDeclarationError as exc:
            print("ENTITY " + exc.entity_name)
            print("FIELD " + exc.field_name)
            print("DETAILS " + exc.details)


    def probe_named(name, cls):
        \"\"\"Like ``probe`` but print a caller-chosen fixture name (for two-phase runs).\"\"\"
        print("FIXTURE " + name)
        try:
            validate_entity_fields([cls])
            print("ACCEPT")
        except EntityFieldDeclarationError as exc:
            print("ENTITY " + exc.entity_name)
            print("FIELD " + exc.field_name)
            print("DETAILS " + exc.details)


    def extra(key, value):
        \"\"\"Print an ``EXTRA key value`` line for construction/edge assertions.\"\"\"
        print("EXTRA " + key + " " + str(value))
    """
)

# Common helper classes every fixture script declares in its own fresh process.
_TARGETS = textwrap.dedent(
    """
    class FieldRulesDomain(BaseDomain):
        name = "field-rules"
        description = "Field declaration rules"

    @exclude_graph_model
    @entity(description="Showcase", domain=FieldRulesDomain)
    class ShowcaseCoreEntity(BaseCoreEntity):
        id: str = Field(description="Showcase identifier")

    @exclude_graph_model
    @entity(description="Gallery", domain=FieldRulesDomain)
    class GalleryCoreEntity(BaseCoreEntity):
        id: str = Field(description="Identifier")

    @entity(description="Dictionary", domain=FieldRulesDomain)
    class CurrencyEnumEntity(BaseEnumEntity):
        symbol: str = Field(description="Currency symbol")
        EUR = value(code="eur", display_name="Euro", symbol="€")

    @exclude_graph_model
    @entity(description="Second dictionary", domain=FieldRulesDomain)
    class CountryEnumEntity(BaseEnumEntity):
        EU = value(code="eu", display_name="Europe")

    @exclude_graph_model
    class EmptyEnumEntity(BaseEnumEntity):
        pass

    @exclude_graph_model
    @entity(description="Hidden dictionary", domain=FieldRulesDomain)
    class HiddenEnumEntity(BaseEnumEntity):
        USD = value(code="usd", display_name="US dollar")

    class DraftStateEntity(BaseStateEntity):
        DRAFT = value(code="draft", display_name="Draft")

    class DraftLifecycle(Lifecycle[DraftStateEntity]):
        pass

    @exclude_graph_model
    @entity(description="Schema host", domain=FieldRulesDomain)
    class HostParams(BaseSchema):
        order_id: str = Field(description="Order identifier")
    """
)


def _run(body: str) -> str:
    """Run ``body`` in a fresh interpreter and return its stdout."""
    result = run_isolated_model(_IMPORTS + "\n" + _TARGETS + "\n" + textwrap.dedent(body))
    assert result.returncode == 0, result.stderr
    return result.stdout


def _blocks(out: str) -> dict[str, dict[str, str]]:
    """Parse ``FIXTURE/ACCEPT|ENTITY/FIELD/DETAILS`` blocks into a per-fixture map."""
    blocks: dict[str, dict[str, str]] = {}
    current: str | None = None
    for line in out.splitlines():
        if line.startswith("FIXTURE "):
            current = line[len("FIXTURE ") :]
            blocks[current] = {}
        elif line == "ACCEPT":
            blocks[current]["accepted"] = "true"
        elif line.startswith("ENTITY "):
            blocks[current]["entity"] = line[len("ENTITY ") :]
        elif line.startswith("FIELD "):
            blocks[current]["field"] = line[len("FIELD ") :]
        elif line.startswith("DETAILS "):
            blocks[current]["details"] = line[len("DETAILS ") :]
    return blocks


def _extras(out: str) -> dict[str, str]:
    """Parse ``EXTRA key value`` lines into a map."""
    result: dict[str, str] = {}
    for line in out.splitlines():
        if line.startswith("EXTRA "):
            _, key, value = line.split(" ", 2)
            result[key] = value
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Script fixtures — each runs once per module.
# ─────────────────────────────────────────────────────────────────────────────

_SHAPE_BODY = """
    @exclude_graph_model
    @entity(description="Bare field", domain=FieldRulesDomain)
    class BareCoreEntity(BaseCoreEntity):
        showcase: ShowcaseCoreEntity = Field(description="Player showcase")

    @exclude_graph_model
    @entity(description="Optional bare field", domain=FieldRulesDomain)
    class OptionalBareCoreEntity(BaseCoreEntity):
        showcase: ShowcaseCoreEntity | None = Field(default=None, description="Showcase")

    @exclude_graph_model
    @entity(description="Bare Annotated field", domain=FieldRulesDomain)
    class BareAnnotatedCoreEntity(BaseCoreEntity):
        showcase: Annotated[ShowcaseCoreEntity, NoInverse()] = Field(description="Showcase")

    @exclude_graph_model
    @entity(description="List of entities", domain=FieldRulesDomain)
    class ListCoreEntity(BaseCoreEntity):
        showcases: list[ShowcaseCoreEntity] = Field(default_factory=list, description="Showcases")

    @exclude_graph_model
    @entity(description="Mapping of entities", domain=FieldRulesDomain)
    class DictCoreEntity(BaseCoreEntity):
        showcases: dict[str, ShowcaseCoreEntity] = Field(default_factory=dict, description="Showcases")

    @exclude_graph_model
    @entity(description="Set of entities", domain=FieldRulesDomain)
    class SetCoreEntity(BaseCoreEntity):
        showcases: set[ShowcaseCoreEntity] = Field(default_factory=set, description="Showcases")

    @exclude_graph_model
    @entity(description="Tuple of entities", domain=FieldRulesDomain)
    class TupleCoreEntity(BaseCoreEntity):
        showcases: tuple[ShowcaseCoreEntity, ...] = Field(default=(), description="Showcases")

    @exclude_graph_model
    @entity(description="Union of entities", domain=FieldRulesDomain)
    class UnionCoreEntity(BaseCoreEntity):
        ref: ShowcaseCoreEntity | GalleryCoreEntity = Field(description="Union")

    @exclude_graph_model
    @entity(description="Mixed collection", domain=FieldRulesDomain)
    class MixedCollectionCoreEntity(BaseCoreEntity):
        ref: tuple[ShowcaseCoreEntity, GalleryCoreEntity] = Field(description="Mixed")

    @exclude_graph_model
    @entity(description="Complete relation", domain=FieldRulesDomain)
    class RelationCoreEntity(BaseCoreEntity):
        showcase: Annotated[AssociationOne[ShowcaseCoreEntity], NoInverse()] = Field(
            description="Player showcase"
        )

    @exclude_graph_model
    @entity(description="Complete many relation", domain=FieldRulesDomain)
    class ManyRelationCoreEntity(BaseCoreEntity):
        showcases: Annotated[AssociationMany[ShowcaseCoreEntity], NoInverse()] = Field(description="Showcases")

    @exclude_graph_model
    @entity(description="Missing direction marker", domain=FieldRulesDomain)
    class MissingDirectionCoreEntity(BaseCoreEntity):
        showcase: AssociationOne[ShowcaseCoreEntity] = Field(description="Showcase")

    @exclude_graph_model
    @entity(description="Duplicate direction markers", domain=FieldRulesDomain)
    class DuplicateDirectionCoreEntity(BaseCoreEntity):
        showcase: Annotated[
            AssociationOne[ShowcaseCoreEntity],
            Inverse(ShowcaseCoreEntity, "player"),
            Inverse(ShowcaseCoreEntity, "player"),
        ] = Field(description="Showcase")

    @exclude_graph_model
    @entity(description="Conflicting direction markers", domain=FieldRulesDomain)
    class ConflictingDirectionCoreEntity(BaseCoreEntity):
        showcase: Annotated[
            AssociationOne[ShowcaseCoreEntity],
            Inverse(ShowcaseCoreEntity, "player"),
            NoInverse(),
        ] = Field(description="Showcase")

    @exclude_graph_model
    @entity(description="Embedded form", domain=FieldRulesDomain)
    class EmbeddedCoreEntity(BaseCoreEntity):
        showcase: Annotated[ShowcaseCoreEntity, NoRelation("embedded showcase snapshot")] = Field(
            description="Showcase snapshot stored as a value"
        )

    @exclude_graph_model
    @entity(description="Marker with a relation", domain=FieldRulesDomain)
    class MarkerWithRelationCoreEntity(BaseCoreEntity):
        showcase: Annotated[AssociationOne[ShowcaseCoreEntity], NoRelation("embedded showcase")] = Field(
            description="Showcase"
        )

    for cls in [
        BareCoreEntity,
        OptionalBareCoreEntity,
        BareAnnotatedCoreEntity,
        ListCoreEntity,
        SetCoreEntity,
        TupleCoreEntity,
        DictCoreEntity,
        UnionCoreEntity,
        MixedCollectionCoreEntity,
        RelationCoreEntity,
        ManyRelationCoreEntity,
        MissingDirectionCoreEntity,
        DuplicateDirectionCoreEntity,
        ConflictingDirectionCoreEntity,
        EmbeddedCoreEntity,
        MarkerWithRelationCoreEntity,
    ]:
        probe(cls)

    relation_node = EntityGraphNode(RelationCoreEntity)
    extra("rel_targets", ",".join(edge.target_node_id for edge in relation_node.relations))
"""

_STATE_BODY = """
    @exclude_graph_model
    @entity(description="State field", domain=FieldRulesDomain)
    class StateFieldCoreEntity(BaseCoreEntity):
        stage: DraftStateEntity = Field(description="Stage")

    @exclude_graph_model
    @entity(description="State in a relation", domain=FieldRulesDomain)
    class StateRelationCoreEntity(BaseCoreEntity):
        stage: Annotated[AssociationOne[DraftStateEntity], NoInverse()] = Field(description="Stage")

    @exclude_graph_model
    @entity(description="State with the marker", domain=FieldRulesDomain)
    class StateMarkerCoreEntity(BaseCoreEntity):
        stage: Annotated[DraftStateEntity, NoRelation("embedded stage snapshot")] = Field(description="Stage")

    for cls in [StateFieldCoreEntity, StateRelationCoreEntity, StateMarkerCoreEntity]:
        probe(cls)
"""

_DICTIONARY_BODY = """
    @exclude_graph_model
    @entity(description="Bare dictionary", domain=FieldRulesDomain)
    class BareDictionaryCoreEntity(BaseCoreEntity):
        id: str = Field(description="Identifier")
        currency: CurrencyEnumEntity = Field(description="Required reference")

    @exclude_graph_model
    @entity(description="Optional bare dictionary", domain=FieldRulesDomain)
    class OptionalBareDictionaryCoreEntity(BaseCoreEntity):
        id: str = Field(description="Identifier")
        currency: CurrencyEnumEntity | None = Field(default=None, description="Optional reference")

    @exclude_graph_model
    @entity(description="Dictionary collection", domain=FieldRulesDomain)
    class DictionaryCollectionCoreEntity(BaseCoreEntity):
        currencies: list[CurrencyEnumEntity] = Field(default_factory=list, description="Currencies")

    @exclude_graph_model
    @entity(description="Dictionary union", domain=FieldRulesDomain)
    class DictionaryUnionCoreEntity(BaseCoreEntity):
        currency: CurrencyEnumEntity | CountryEnumEntity = Field(description="Union")

    @exclude_graph_model
    @entity(description="Complete dictionary selection", domain=FieldRulesDomain)
    class DictionarySelectionCoreEntity(BaseCoreEntity):
        id: str = Field(description="Identifier")
        currency: Annotated[AssociationOne[CurrencyEnumEntity], NoInverse()] = Field(description="Currency")

    @exclude_graph_model
    @entity(description="Nullable dictionary selection", domain=FieldRulesDomain)
    class NullableDictionarySelectionCoreEntity(BaseCoreEntity):
        id: str = Field(description="Identifier")
        currency: Annotated[AssociationOne[CurrencyEnumEntity] | None, NoInverse()] = Field(
            default=None, description="Currency"
        )

    @exclude_graph_model
    @entity(description="Dictionary selection with inverse", domain=FieldRulesDomain)
    class InverseDictionarySelectionCoreEntity(BaseCoreEntity):
        currency: Annotated[
            AssociationOne[CurrencyEnumEntity],
            Inverse(field_name="currency"),
        ] = Field(description="Currency")

    @exclude_graph_model
    @entity(description="Many of a dictionary", domain=FieldRulesDomain)
    class AssociationManyDictionaryCoreEntity(BaseCoreEntity):
        currency: Annotated[AssociationMany[CurrencyEnumEntity], NoInverse()] = Field(description="Currency")

    @exclude_graph_model
    @entity(description="Composite of a dictionary", domain=FieldRulesDomain)
    class CompositeOneDictionaryCoreEntity(BaseCoreEntity):
        currency: Annotated[CompositeOne[CurrencyEnumEntity], NoInverse()] = Field(description="Currency")

    @exclude_graph_model
    @entity(description="Generalization of a dictionary", domain=FieldRulesDomain)
    class GeneralizationDictionaryCoreEntity(BaseCoreEntity):
        currency: Annotated[Generalization[CurrencyEnumEntity], NoInverse()] = Field(description="Currency")

    @exclude_graph_model
    @entity(description="Empty catalogue", domain=FieldRulesDomain)
    class EmptyCatalogueCoreEntity(BaseCoreEntity):
        currency: Annotated[AssociationOne[EmptyEnumEntity], NoInverse()] = Field(description="Currency")

    @exclude_graph_model
    @entity(description="Hidden dictionary reference", domain=FieldRulesDomain)
    class HiddenDictionaryCoreEntity(BaseCoreEntity):
        currency: Annotated[AssociationOne[HiddenEnumEntity], NoInverse()] = Field(description="Currency")

    @exclude_graph_model
    @entity(description="Spec dictionary host", domain=FieldRulesDomain)
    class SpecDictionarySpecEntity(BaseSpecEntity):
        id: str = Field(description="Identifier")
        currency: CurrencyEnumEntity = Field(description="Currency")

    @exclude_graph_model
    @entity(description="Assoc dictionary host", domain=FieldRulesDomain)
    class AssocDictionaryAssocEntity(BaseAssocEntity):
        id: str = Field(description="Identifier")
        currency: CurrencyEnumEntity = Field(description="Currency")

    @exclude_graph_model
    @entity(description="Detail dictionary host", domain=FieldRulesDomain)
    class DetailDictionaryDetailEntity(BaseDetailEntity):
        id: str = Field(description="Identifier")
        currency: CurrencyEnumEntity = Field(description="Currency")

    for cls in [
        BareDictionaryCoreEntity,
        OptionalBareDictionaryCoreEntity,
        DictionaryCollectionCoreEntity,
        DictionaryUnionCoreEntity,
        DictionarySelectionCoreEntity,
        NullableDictionarySelectionCoreEntity,
        InverseDictionarySelectionCoreEntity,
        AssociationManyDictionaryCoreEntity,
        CompositeOneDictionaryCoreEntity,
        GeneralizationDictionaryCoreEntity,
        EmptyCatalogueCoreEntity,
        HiddenDictionaryCoreEntity,
        SpecDictionarySpecEntity,
        AssocDictionaryAssocEntity,
        DetailDictionaryDetailEntity,
    ]:
        probe(cls)
"""

_METADATA_BODY = """
    @exclude_graph_model
    @entity(description="Required relation", domain=FieldRulesDomain)
    class RequiredRelationCoreEntity(BaseCoreEntity):
        showcase: Annotated[AssociationOne[ShowcaseCoreEntity], NoInverse()] = Field(description="Required showcase")

    @exclude_graph_model
    @entity(description="Nullable required relation", domain=FieldRulesDomain)
    class NullableRequiredCoreEntity(BaseCoreEntity):
        showcase: Annotated[AssociationOne[ShowcaseCoreEntity] | None, NoInverse()] = Field(description="Nullable showcase")

    @exclude_graph_model
    @entity(description="Omittable relation", domain=FieldRulesDomain)
    class OmittableCoreEntity(BaseCoreEntity):
        showcase: Annotated[AssociationOne[ShowcaseCoreEntity] | None, NoInverse()] = Field(
            default=None, description="Omittable showcase"
        )

    @exclude_graph_model
    @entity(description="Non-nullable default", domain=FieldRulesDomain)
    class NonNullableDefaultCoreEntity(BaseCoreEntity):
        showcase: Annotated[AssociationOne[ShowcaseCoreEntity], NoInverse()] = Field(default=None, description="Showcase")

    @exclude_graph_model
    @entity(description="Prebuilt default", domain=FieldRulesDomain)
    class PrebuiltDefaultCoreEntity(BaseCoreEntity):
        showcase: Annotated[AssociationOne[ShowcaseCoreEntity], NoInverse()] = Field(
            default=AssociationOne(id="x"), description="Showcase"
        )

    _FACTORY_CALLS = []

    def _factory():
        _FACTORY_CALLS.append(True)
        return None

    @exclude_graph_model
    @entity(description="Factory default", domain=FieldRulesDomain)
    class FactoryCoreEntity(BaseCoreEntity):
        showcase: Annotated[AssociationOne[ShowcaseCoreEntity] | None, NoInverse()] = Field(
            default_factory=_factory, description="Showcase"
        )

    @exclude_graph_model
    @entity(description="Blank description", domain=FieldRulesDomain)
    class BlankDescriptionCoreEntity(BaseCoreEntity):
        showcase: Annotated[AssociationOne[ShowcaseCoreEntity], NoInverse()] = Field(description="   ")

    @exclude_graph_model
    @entity(description="Missing description", domain=FieldRulesDomain)
    class MissingDescriptionCoreEntity(BaseCoreEntity):
        showcase: Annotated[AssociationOne[ShowcaseCoreEntity], NoInverse()] = Field()

    @exclude_graph_model
    @entity(description="Hidden edge", domain=FieldRulesDomain)
    class HiddenEdgeCoreEntity(BaseCoreEntity):
        showcase: Annotated[AssociationOne[ShowcaseCoreEntity], NoInverse(), NoGraphEdge()] = Field()

    @exclude_graph_model
    @entity(description="Inner syntax", domain=FieldRulesDomain)
    class InnerSyntaxCoreEntity(BaseCoreEntity):
        showcase: Annotated[AssociationOne[ShowcaseCoreEntity], NoInverse(), Field(description="Inner showcase")] = Field()

    @exclude_graph_model
    @entity(description="Both syntaxes", domain=FieldRulesDomain)
    class BothSyntaxesCoreEntity(BaseCoreEntity):
        showcase: Annotated[AssociationOne[ShowcaseCoreEntity], NoInverse(), Field(description="Inner showcase")] = Field(
            description="Outer showcase"
        )

    @exclude_graph_model
    @entity(description="Relation base", domain=FieldRulesDomain)
    class RelationBaseCoreEntity(BaseCoreEntity):
        showcase: Annotated[AssociationOne[ShowcaseCoreEntity], NoInverse()] = Field(default=None, description="Showcase")

    @exclude_graph_model
    @entity(description="Inherited relation", domain=FieldRulesDomain)
    class InheritedRelationCoreEntity(RelationBaseCoreEntity):
        id: str = Field(description="Identifier")

    @exclude_graph_model
    @entity(description="Untouched forms", domain=FieldRulesDomain)
    class OrdinaryCoreEntity(BaseCoreEntity):
        id: str = Field(description="Identifier")
        age: int | None = Field(default=None, description="Age")
        currency: Annotated[AssociationOne[CurrencyEnumEntity], NoInverse()] = Field(description="Currency")
        lifecycle: DraftLifecycle = Field(description="Lifecycle")
        params: HostParams = Field(description="Parameters")

    for cls in [
        RequiredRelationCoreEntity,
        NullableRequiredCoreEntity,
        OmittableCoreEntity,
        NonNullableDefaultCoreEntity,
        PrebuiltDefaultCoreEntity,
        FactoryCoreEntity,
        BlankDescriptionCoreEntity,
        MissingDescriptionCoreEntity,
        HiddenEdgeCoreEntity,
        InnerSyntaxCoreEntity,
        BothSyntaxesCoreEntity,
        RelationBaseCoreEntity,
        InheritedRelationCoreEntity,
        OrdinaryCoreEntity,
    ]:
        probe(cls)

    extra("factory_calls", str(len(_FACTORY_CALLS)))

    try:
        RequiredRelationCoreEntity()
        extra("req_construct", "ok")
    except ValidationError:
        extra("req_construct", "ValidationError")
    try:
        RequiredRelationCoreEntity(showcase=None)
        extra("req_none", "ok")
    except ValidationError:
        extra("req_none", "ValidationError")
    try:
        NullableRequiredCoreEntity()
        extra("nullable_required_construct", "ok")
    except ValidationError:
        extra("nullable_required_construct", "ValidationError")
    extra("nullable_required_none", str(NullableRequiredCoreEntity(showcase=None).showcase))
    extra("omittable_none", str(OmittableCoreEntity().showcase))
    extra("omittable_explicit_none", str(OmittableCoreEntity(showcase=None).showcase))

    extra("inner_desc", InnerSyntaxCoreEntity.model_fields["showcase"].description)
    extra("outer_desc", BothSyntaxesCoreEntity.model_fields["showcase"].description)
"""


@pytest.fixture(scope="module")
def shape_out() -> dict[str, dict[str, str]]:
    """The structural-shape fixture blocks and edge extras."""
    return _blocks(_run(_SHAPE_BODY))


@pytest.fixture(scope="module")
def shape_extras() -> dict[str, str]:
    """The edge extras produced alongside the shape fixtures."""
    return _extras(_run(_SHAPE_BODY))


@pytest.fixture(scope="module")
def state_out() -> dict[str, dict[str, str]]:
    """The state-refusal fixture blocks."""
    return _blocks(_run(_STATE_BODY))


@pytest.fixture(scope="module")
def dictionary_out() -> dict[str, dict[str, str]]:
    """The dictionary fixture blocks."""
    return _blocks(_run(_DICTIONARY_BODY))


@pytest.fixture(scope="module")
def metadata_out() -> dict[str, dict[str, str]]:
    """The relation-metadata fixture blocks."""
    return _blocks(_run(_METADATA_BODY))


@pytest.fixture(scope="module")
def metadata_extras() -> dict[str, str]:
    """The relation-metadata construction extras."""
    return _extras(_run(_METADATA_BODY))


# ─────────────────────────────────────────────────────────────────────────────
# Structural shape
# ─────────────────────────────────────────────────────────────────────────────


def test_a_bare_entity_field_is_refused_naming_the_form(shape_out: dict[str, dict[str, str]]) -> None:
    """The original defect: a structural entity written as a scalar."""
    block = shape_out["BareCoreEntity"]

    assert block["entity"] == "BareCoreEntity"
    assert block["field"] == "showcase"
    assert "ShowcaseCoreEntity" in block["details"]
    assert "AssociationOne" in block["details"]


def test_a_bare_optional_entity_field_is_refused(shape_out: dict[str, dict[str, str]]) -> None:
    """`X | None` without a container is not a declaration either."""
    block = shape_out["OptionalBareCoreEntity"]

    assert block["field"] == "showcase"
    assert "AssociationOne" in block["details"]


def test_a_bare_annotated_entity_without_container_is_refused(shape_out: dict[str, dict[str, str]]) -> None:
    """A marker around a bare entity does not make it a relationship."""
    block = shape_out["BareAnnotatedCoreEntity"]

    assert block["field"] == "showcase"
    assert "AssociationOne" in block["details"]


@pytest.mark.parametrize("name", ["ListCoreEntity", "SetCoreEntity", "TupleCoreEntity"])
def test_a_collection_of_entities_is_refused(name: str, shape_out: dict[str, dict[str, str]]) -> None:
    """A container of an entity is not a relation; the many form is named instead."""
    block = shape_out[name]

    assert block["field"] == "showcases"
    assert "AssociationMany" in block["details"]


def test_a_union_of_entities_names_both_and_asks_for_two_fields(shape_out: dict[str, dict[str, str]]) -> None:
    """A union is not a collection, and it has no single container."""
    details = shape_out["UnionCoreEntity"]["details"]

    assert "union" in details
    assert "ShowcaseCoreEntity" in details
    assert "GalleryCoreEntity" in details
    assert "AssociationMany" not in details


def test_a_heterogeneous_collection_names_every_entity(shape_out: dict[str, dict[str, str]]) -> None:
    """One many-relation cannot point at two entities."""
    details = shape_out["MixedCollectionCoreEntity"]["details"]

    assert "collection of 2 entities" in details
    assert "ShowcaseCoreEntity" in details
    assert "GalleryCoreEntity" in details


def test_a_mapping_is_described_as_a_mapping(shape_out: dict[str, dict[str, str]]) -> None:
    """A mapping is not a relation, and no many-relation fits it."""
    details = shape_out["DictCoreEntity"]["details"]

    assert "mapping" in details
    assert "ShowcaseCoreEntity" in details


def test_the_complete_relation_form_builds_an_edge(
    shape_out: dict[str, dict[str, str]], shape_extras: dict[str, str]
) -> None:
    """A complete relation — container, one direction marker, description — is accepted."""
    assert shape_out["RelationCoreEntity"].get("accepted")
    assert shape_out["ManyRelationCoreEntity"].get("accepted")

    assert "ShowcaseCoreEntity" in shape_extras["rel_targets"]


def test_a_relation_without_a_direction_marker_is_refused(shape_out: dict[str, dict[str, str]]) -> None:
    """A container with no direction marker names neither an inverse nor a one-way edge."""
    details = shape_out["MissingDirectionCoreEntity"]["details"]

    assert "direction marker" in details


def test_duplicate_direction_markers_are_refused(shape_out: dict[str, dict[str, str]]) -> None:
    """Two direction markers are one too many."""
    details = shape_out["DuplicateDirectionCoreEntity"]["details"]

    assert "2 direction markers" in details


def test_conflicting_direction_markers_are_refused(shape_out: dict[str, dict[str, str]]) -> None:
    """Inverse and NoInverse together contradict each other."""
    details = shape_out["ConflictingDirectionCoreEntity"]["details"]

    assert "2 direction markers" in details


def test_the_embedded_form_is_now_refused(shape_out: dict[str, dict[str, str]]) -> None:
    """NoRelation no longer declares an embedded value."""
    details = shape_out["EmbeddedCoreEntity"]["details"]

    assert "NoRelation" in details


def test_the_embedded_marker_cannot_accompany_a_relation(shape_out: dict[str, dict[str, str]]) -> None:
    """A field either has a complete relation or it does not."""
    details = shape_out["MarkerWithRelationCoreEntity"]["details"]

    assert "NoRelation" in details


# ─────────────────────────────────────────────────────────────────────────────
# State
# ─────────────────────────────────────────────────────────────────────────────


def test_a_state_entity_field_names_the_lifecycle_form(state_out: dict[str, dict[str, str]]) -> None:
    """A state is neither a relation nor a plain field."""
    block = state_out["StateFieldCoreEntity"]

    assert block["field"] == "stage"
    assert "Lifecycle[...]" in block["details"]


def test_a_state_entity_inside_a_relation_container_is_refused(state_out: dict[str, dict[str, str]]) -> None:
    """Wrapping a state in a relation container does not give it a field form."""
    assert "Lifecycle[...]" in state_out["StateRelationCoreEntity"]["details"]


def test_the_embedded_marker_does_not_apply_to_a_state(state_out: dict[str, dict[str, str]]) -> None:
    """The marker is for Core, Assoc, Detail and Spec only."""
    assert "Lifecycle[...]" in state_out["StateMarkerCoreEntity"]["details"]


# ─────────────────────────────────────────────────────────────────────────────
# Dictionary
# ─────────────────────────────────────────────────────────────────────────────


def test_a_bare_dictionary_reference_is_refused(dictionary_out: dict[str, dict[str, str]]) -> None:
    """A bare dictionary field must become an explicit AssociationOne[D]."""
    details = dictionary_out["BareDictionaryCoreEntity"]["details"]

    assert "AssociationOne" in details
    assert "NoInverse" in details


def test_a_nullable_bare_dictionary_is_refused(dictionary_out: dict[str, dict[str, str]]) -> None:
    """``D | None`` is still a bare dictionary, not a complete declaration."""
    details = dictionary_out["OptionalBareDictionaryCoreEntity"]["details"]

    assert "AssociationOne" in details


def test_a_collection_of_dictionary_values_is_refused(dictionary_out: dict[str, dict[str, str]]) -> None:
    """A collection of dictionary values has no declared form."""
    details = dictionary_out["DictionaryCollectionCoreEntity"]["details"]

    assert "AssociationOne" in details
    assert "CurrencyEnumEntity" in details


def test_a_union_of_two_dictionaries_is_refused(dictionary_out: dict[str, dict[str, str]]) -> None:
    """A field names one dictionary, not a choice between two."""
    details = dictionary_out["DictionaryUnionCoreEntity"]["details"]

    assert "more than one dictionary" in details


def test_the_complete_dictionary_selection_is_accepted(dictionary_out: dict[str, dict[str, str]]) -> None:
    """``AssociationOne[D]`` with ``NoInverse()`` is the complete Enum declaration."""
    assert dictionary_out["DictionarySelectionCoreEntity"].get("accepted")
    assert dictionary_out["NullableDictionarySelectionCoreEntity"].get("accepted")


def test_an_inverse_on_a_dictionary_selection_is_refused(dictionary_out: dict[str, dict[str, str]]) -> None:
    """A dictionary selection is unpaired; it cannot declare an inverse."""
    details = dictionary_out["InverseDictionarySelectionCoreEntity"]["details"]

    assert "NoInverse" in details


@pytest.mark.parametrize(
    "name",
    ["AssociationManyDictionaryCoreEntity", "CompositeOneDictionaryCoreEntity", "GeneralizationDictionaryCoreEntity"],
)
def test_a_non_association_container_around_a_dictionary_is_refused(
    name: str, dictionary_out: dict[str, dict[str, str]]
) -> None:
    """Only AssociationOne is a legal dictionary relationship."""
    details = dictionary_out[name]["details"]

    assert "AssociationOne" in details
    assert "CurrencyEnumEntity" in details


def test_an_empty_dictionary_is_refused_at_the_declaration_boundary(dictionary_out: dict[str, dict[str, str]]) -> None:
    """A dictionary with no values could never fill the field, and the rule says so first."""
    details = dictionary_out["EmptyCatalogueCoreEntity"]["details"]

    assert "declares no values" in details


def test_a_dictionary_outside_the_graph_is_refused(dictionary_out: dict[str, dict[str, str]]) -> None:
    """A reference edge needs a node; an excluded dictionary has none."""
    details = dictionary_out["HiddenDictionaryCoreEntity"]["details"]

    assert "no node in the graph" in details


@pytest.mark.parametrize(
    "name",
    ["SpecDictionarySpecEntity", "AssocDictionaryAssocEntity", "DetailDictionaryDetailEntity"],
)
def test_a_bare_dictionary_is_refused_on_every_structural_host(
    name: str, dictionary_out: dict[str, dict[str, str]]
) -> None:
    """The host's kind does not change the dictionary rule."""
    assert "AssociationOne" in dictionary_out[name]["details"]


# ─────────────────────────────────────────────────────────────────────────────
# Relation metadata discipline and untouched controls
# ─────────────────────────────────────────────────────────────────────────────


def test_untouched_forms_pass_unchanged(metadata_out: dict[str, dict[str, str]]) -> None:
    """A complete dictionary selection, a lifecycle, a schema type and a scalar pass."""
    assert metadata_out["OrdinaryCoreEntity"].get("accepted")


def test_a_required_relation_must_be_supplied(
    metadata_out: dict[str, dict[str, str]], metadata_extras: dict[str, str]
) -> None:
    """The default contract, row one: no default at all."""
    assert metadata_out["RequiredRelationCoreEntity"].get("accepted")

    assert metadata_extras["req_construct"] == "ValidationError"
    assert metadata_extras["req_none"] == "ValidationError"


def test_a_nullable_required_relation_still_must_be_supplied(
    metadata_out: dict[str, dict[str, str]], metadata_extras: dict[str, str]
) -> None:
    """The default contract, row two: ``| None`` alone gives no default."""
    assert metadata_out["NullableRequiredCoreEntity"].get("accepted")

    assert metadata_extras["nullable_required_construct"] == "ValidationError"
    assert metadata_extras["nullable_required_none"] == "None"


def test_an_omittable_relation_yields_none(
    metadata_out: dict[str, dict[str, str]], metadata_extras: dict[str, str]
) -> None:
    """The default contract, row three: a nullable relation with an explicit ``None``."""
    assert metadata_out["OmittableCoreEntity"].get("accepted")

    assert metadata_extras["omittable_none"] == "None"
    assert metadata_extras["omittable_explicit_none"] == "None"


def test_none_on_a_non_nullable_relation_is_refused_at_declaration(metadata_out: dict[str, dict[str, str]]) -> None:
    """The default contract, row four: ``default=None`` needs a nullable annotation."""
    block = metadata_out["NonNullableDefaultCoreEntity"]

    assert block["field"] == "showcase"
    assert "None" in block["details"]


def test_a_prebuilt_relation_default_is_refused(metadata_out: dict[str, dict[str, str]]) -> None:
    """A value in the default slot is not a default the framework can honour."""
    assert metadata_out["PrebuiltDefaultCoreEntity"]["field"] == "showcase"


def test_a_factory_is_refused_and_never_executed(
    metadata_out: dict[str, dict[str, str]], metadata_extras: dict[str, str]
) -> None:
    """Refusing a factory must not run user code."""
    assert metadata_out["FactoryCoreEntity"]["field"] == "showcase"
    assert metadata_extras["factory_calls"] == "0"


@pytest.mark.parametrize("name", ["BlankDescriptionCoreEntity", "MissingDescriptionCoreEntity", "HiddenEdgeCoreEntity"])
def test_a_relation_without_a_description_is_refused(name: str, metadata_out: dict[str, dict[str, str]]) -> None:
    """A missing, blank or whitespace-only description is refused, hidden edge or not."""
    assert "description" in metadata_out[name]["details"]


def test_both_field_syntaxes_feed_one_description(
    metadata_out: dict[str, dict[str, str]], metadata_extras: dict[str, str]
) -> None:
    """The assignment wins over the inner ``Field``, and each alone is enough."""
    assert metadata_out["InnerSyntaxCoreEntity"].get("accepted")
    assert metadata_out["BothSyntaxesCoreEntity"].get("accepted")

    assert metadata_extras["inner_desc"] == "Inner showcase"
    assert metadata_extras["outer_desc"] == "Outer showcase"


def test_an_inherited_relation_is_judged(metadata_out: dict[str, dict[str, str]]) -> None:
    """A relation declared on a base class obeys the same rules on the class that inherits it."""
    block = metadata_out["InheritedRelationCoreEntity"]

    assert block["field"] == "showcase"


# ─────────────────────────────────────────────────────────────────────────────
# Parent-process checks — no invalid fixture is loaded here.
# ─────────────────────────────────────────────────────────────────────────────


def test_a_blank_marker_reason_is_refused_at_construction() -> None:
    """The reason is the point of the marker, so it is required."""
    with pytest.raises(ValueError, match="whitespace-only"):
        NoRelation("   ")


@exclude_graph_model
class _KindCoreEntity(BaseCoreEntity):
    pass


@exclude_graph_model
class _KindEnumEntity(BaseEnumEntity):
    pass


@exclude_graph_model
class _KindStateEntity(BaseStateEntity):
    pass


def test_the_kind_classifier_names_the_dictionary_kind() -> None:
    """The dictionary is a kind of its own, next to the structural ones and the state."""
    assert _kind_of(_KindEnumEntity) == "Enum"
    assert _kind_of(_KindCoreEntity) == "Core"
    assert _kind_of(_KindStateEntity) == "State"
    assert _kind_of(str) is None


def test_global_validation_is_not_poisoned_by_subprocess_isolated_invalid_declarations() -> None:
    """The invalid fixtures live only in subprocesses, so the shared model stays clean."""
    declared = {cls.__name__ for cls in declared_entity_classes()}

    assert "BareCoreEntity" not in declared
    assert "ListCoreEntity" not in declared
    assert "BareDictionaryCoreEntity" not in declared


def test_the_graph_build_runs_the_field_pass(monkeypatch: pytest.MonkeyPatch) -> None:
    """The rule belongs to the build: a caller cannot publish a graph without it."""
    from aoa.action_machine.graph.core.node_graph_coordinator import NodeGraphCoordinator
    from aoa.action_machine.graph.validators import entity_field_validator as validator_module

    calls: list[bool] = []
    monkeypatch.setattr(validator_module, "validate_entity_fields", lambda entities=None: calls.append(True))

    NodeGraphCoordinator().build([])

    assert calls == [True]
