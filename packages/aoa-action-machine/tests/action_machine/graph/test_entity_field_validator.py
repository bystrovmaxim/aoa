# tests/action_machine/graph/test_entity_field_validator.py
"""
Tests for ``validate_entity_fields`` — a structural-entity field must declare its form.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A field whose resolved type is a structural entity is a relation by nature. Written as
a bare type, a collection, a bare optional, or a state entity, it used to build and to
produce a column that meant nothing. These tests pin the four refusals, the two legal
forms, and the forms that stay untouched: a dictionary reference, a lifecycle, a schema
type and an ordinary scalar.

Every refused fixture is ``@exclude_graph_model`` so the class exists for the explicit
call and never joins the global model other tests build.
"""

from __future__ import annotations

from typing import Annotated

import pytest
from pydantic import Field, ValidationError

from aoa.action_machine.domain import (
    AssociationMany,
    AssociationOne,
    BaseCoreEntity,
    BaseDomain,
    BaseEnumEntity,
    Inverse,
    NoGraphEdge,
    NoInverse,
    NoRelation,
    value,
)
from aoa.action_machine.domain.exceptions import EntityFieldDeclarationError
from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
from aoa.action_machine.graph.nodes.entity_graph_node import EntityGraphNode
from aoa.action_machine.graph.validators.entity_field_validator import validate_entity_fields
from aoa.action_machine.graph.validators.entity_specialization_validator import declared_entity_classes
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.model.base_schema import BaseSchema

from ...support.domain_model.entities import DraftLifecycle, DraftStateEntity


class FieldRulesDomain(BaseDomain):
    """The domain every fixture in this module belongs to."""

    name = "field-rules"
    description = "Field declaration rules"


@exclude_graph_model
@entity(description="Showcase", domain=FieldRulesDomain)
class ShowcaseCoreEntity(BaseCoreEntity):
    """The entity other fields point at."""

    id: str = Field(description="Showcase identifier")


@exclude_graph_model
@entity(description="Dictionary", domain=FieldRulesDomain)
class CurrencyEnumEntity(BaseEnumEntity):
    """A dictionary reference the rule leaves alone."""

    symbol: str = Field(description="Currency symbol")

    EUR = value(code="eur", display_name="Euro", symbol="€")


@exclude_graph_model
@entity(description="Schema host", domain=FieldRulesDomain)
class HostParams(BaseSchema):
    """A schema type the rule leaves alone."""

    order_id: str = Field(description="Order identifier")


@exclude_graph_model
@entity(description="Bare field", domain=FieldRulesDomain)
class BareCoreEntity(BaseCoreEntity):
    """Declare a structural entity as a scalar — the defect this rule refuses."""

    showcase: ShowcaseCoreEntity = Field(description="Player showcase")


@exclude_graph_model
@entity(description="Optional bare field", domain=FieldRulesDomain)
class OptionalBareCoreEntity(BaseCoreEntity):
    """Declare a bare optional of a structural entity."""

    showcase: ShowcaseCoreEntity | None = Field(default=None, description="Showcase")


@exclude_graph_model
@entity(description="List of entities", domain=FieldRulesDomain)
class ListCoreEntity(BaseCoreEntity):
    """Declare a collection of a structural entity."""

    showcases: list[ShowcaseCoreEntity] = Field(default_factory=list, description="Showcases")


@exclude_graph_model
@entity(description="Mapping of entities", domain=FieldRulesDomain)
class DictCoreEntity(BaseCoreEntity):
    """Declare a mapping of a structural entity."""

    showcases: dict[str, ShowcaseCoreEntity] = Field(default_factory=dict, description="Showcases")


@exclude_graph_model
@entity(description="Set of entities", domain=FieldRulesDomain)
class SetCoreEntity(BaseCoreEntity):
    """Declare a set of a structural entity."""

    showcases: set[ShowcaseCoreEntity] = Field(default_factory=set, description="Showcases")


@exclude_graph_model
@entity(description="Tuple of entities", domain=FieldRulesDomain)
class TupleCoreEntity(BaseCoreEntity):
    """Declare a tuple of a structural entity."""

    showcases: tuple[ShowcaseCoreEntity, ...] = Field(default=(), description="Showcases")


@exclude_graph_model
@entity(description="State field", domain=FieldRulesDomain)
class StateFieldCoreEntity(BaseCoreEntity):
    """Declare a state entity as a field."""

    stage: DraftStateEntity = Field(description="Stage")


@exclude_graph_model
@entity(description="State in a relation", domain=FieldRulesDomain)
class StateRelationCoreEntity(BaseCoreEntity):
    """Wrap a state entity in a relation container."""

    stage: Annotated[AssociationOne[DraftStateEntity], NoInverse()] = Field(description="Stage")


@exclude_graph_model
@entity(description="State with the marker", domain=FieldRulesDomain)
class StateMarkerCoreEntity(BaseCoreEntity):
    """Mark a state entity as an embedded value — still refused."""

    stage: Annotated[DraftStateEntity, NoRelation("embedded stage snapshot")] = Field(description="Stage")


@exclude_graph_model
@entity(description="Marker on a dictionary", domain=FieldRulesDomain)
class MarkerOnEnumCoreEntity(BaseCoreEntity):
    """Mark a dictionary reference, which no marker applies to."""

    currency: Annotated[CurrencyEnumEntity, NoRelation("embedded currency")] = Field(description="Currency")


@exclude_graph_model
@entity(description="Marker with a relation", domain=FieldRulesDomain)
class MarkerWithRelationCoreEntity(BaseCoreEntity):
    """Combine the marker with a relation container — contradictory."""

    showcase: Annotated[AssociationOne[ShowcaseCoreEntity], NoRelation("embedded showcase")] = Field(
        description="Showcase"
    )


@exclude_graph_model
@entity(description="Forward reference", domain=FieldRulesDomain)
class ForwardCoreEntity(BaseCoreEntity):
    """Name its target before that target exists — a genuine forward reference."""

    showcase: LaterCoreEntity = Field(description="Showcase")


@exclude_graph_model
@entity(description="Forward target", domain=FieldRulesDomain)
class LaterCoreEntity(BaseCoreEntity):
    """Be the class the forward reference names."""

    id: str = Field(description="Identifier")


@exclude_graph_model
@entity(description="Relation form", domain=FieldRulesDomain)
class RelationCoreEntity(BaseCoreEntity):
    """Declare the field as a relation — the legal first form."""

    showcase: Annotated[AssociationOne[ShowcaseCoreEntity], Inverse(ShowcaseCoreEntity, "player")] = Field(
        description="Player showcase"
    )


@exclude_graph_model
@entity(description="Many relation form", domain=FieldRulesDomain)
class ManyRelationCoreEntity(BaseCoreEntity):
    """Declare a collection as a many relation — the legal many form."""

    showcases: Annotated[AssociationMany[ShowcaseCoreEntity], NoInverse()] = Field(description="Showcases")


@exclude_graph_model
@entity(description="Embedded form", domain=FieldRulesDomain)
class EmbeddedCoreEntity(BaseCoreEntity):
    """Declare the field as an embedded value — the legal second form."""

    showcase: Annotated[ShowcaseCoreEntity, NoRelation("embedded showcase snapshot")] = Field(
        description="Showcase snapshot stored as a value"
    )


@exclude_graph_model
@entity(description="Untouched forms", domain=FieldRulesDomain)
class OrdinaryCoreEntity(BaseCoreEntity):
    """Keep every form the rule leaves alone on one class."""

    id: str = Field(description="Identifier")
    age: int | None = Field(default=None, description="Age")
    currency: CurrencyEnumEntity = Field(description="Currency")
    lifecycle: DraftLifecycle = Field(description="Lifecycle")
    params: HostParams = Field(description="Parameters")


@exclude_graph_model
@entity(description="Required relation", domain=FieldRulesDomain)
class RequiredRelationCoreEntity(BaseCoreEntity):
    """Declare a relation that must be supplied."""

    showcase: Annotated[AssociationOne[ShowcaseCoreEntity], NoInverse()] = Field(
        description="Required showcase"
    )


@exclude_graph_model
@entity(description="Nullable required relation", domain=FieldRulesDomain)
class NullableRequiredCoreEntity(BaseCoreEntity):
    """Declare a nullable relation that must still be supplied."""

    showcase: Annotated[AssociationOne[ShowcaseCoreEntity] | None, NoInverse()] = Field(
        description="Nullable showcase"
    )


@exclude_graph_model
@entity(description="Omittable relation", domain=FieldRulesDomain)
class OmittableCoreEntity(BaseCoreEntity):
    """Declare a nullable relation that may be omitted."""

    showcase: Annotated[AssociationOne[ShowcaseCoreEntity] | None, NoInverse()] = Field(
        default=None, description="Omittable showcase"
    )


@exclude_graph_model
@entity(description="Non-nullable default", domain=FieldRulesDomain)
class NonNullableDefaultCoreEntity(BaseCoreEntity):
    """Default ``None`` on a relation that does not allow it."""

    showcase: Annotated[AssociationOne[ShowcaseCoreEntity], NoInverse()] = Field(
        default=None, description="Showcase"
    )


@exclude_graph_model
@entity(description="Prebuilt default", domain=FieldRulesDomain)
class PrebuiltDefaultCoreEntity(BaseCoreEntity):
    """A prebuilt relation container as the default."""

    showcase: Annotated[AssociationOne[ShowcaseCoreEntity], NoInverse()] = Field(
        default=AssociationOne(id="x"), description="Showcase"
    )


_FACTORY_CALLS: list[bool] = []


def _factory() -> None:
    """Record that the framework executed a factory it must not execute."""
    _FACTORY_CALLS.append(True)
    return None


@exclude_graph_model
@entity(description="Factory default", domain=FieldRulesDomain)
class FactoryCoreEntity(BaseCoreEntity):
    """A factory as the default, even one returning ``None``."""

    showcase: Annotated[AssociationOne[ShowcaseCoreEntity] | None, NoInverse()] = Field(
        default_factory=_factory, description="Showcase"
    )


@exclude_graph_model
@entity(description="Blank description", domain=FieldRulesDomain)
class BlankDescriptionCoreEntity(BaseCoreEntity):
    """A relation whose description is whitespace only."""

    showcase: Annotated[AssociationOne[ShowcaseCoreEntity], NoInverse()] = Field(description="   ")


@exclude_graph_model
@entity(description="Missing description", domain=FieldRulesDomain)
class MissingDescriptionCoreEntity(BaseCoreEntity):
    """A relation with no description at all."""

    showcase: Annotated[AssociationOne[ShowcaseCoreEntity], NoInverse()] = Field()


@exclude_graph_model
@entity(description="Hidden edge", domain=FieldRulesDomain)
class HiddenEdgeCoreEntity(BaseCoreEntity):
    """A relation whose edge is hidden, with no description."""

    showcase: Annotated[AssociationOne[ShowcaseCoreEntity], NoInverse(), NoGraphEdge()] = Field()


@exclude_graph_model
@entity(description="Inner syntax", domain=FieldRulesDomain)
class InnerSyntaxCoreEntity(BaseCoreEntity):
    """A description supplied by the ``Field`` inside ``Annotated``."""

    showcase: Annotated[
        AssociationOne[ShowcaseCoreEntity], NoInverse(), Field(description="Inner showcase")
    ] = Field()


@exclude_graph_model
@entity(description="Both syntaxes", domain=FieldRulesDomain)
class BothSyntaxesCoreEntity(BaseCoreEntity):
    """A description supplied twice: the assignment wins."""

    showcase: Annotated[
        AssociationOne[ShowcaseCoreEntity], NoInverse(), Field(description="Inner showcase")
    ] = Field(description="Outer showcase")


@exclude_graph_model
@entity(description="Relation base", domain=FieldRulesDomain)
class RelationBaseCoreEntity(BaseCoreEntity):
    """Declare a relation on a base class."""

    showcase: Annotated[AssociationOne[ShowcaseCoreEntity], NoInverse()] = Field(
        default=None, description="Showcase"
    )


@exclude_graph_model
@entity(description="Inherited relation", domain=FieldRulesDomain)
class InheritedRelationCoreEntity(RelationBaseCoreEntity):
    """Inherit a relation the rule must still judge."""

    id: str = Field(description="Identifier")


def _refusal(entity_cls: type) -> EntityFieldDeclarationError:
    """Return the refusal raised for one class."""
    with pytest.raises(EntityFieldDeclarationError) as caught:
        validate_entity_fields([entity_cls])
    return caught.value


def test_a_bare_entity_field_is_refused_naming_the_forms() -> None:
    """The original defect: a structural entity written as a scalar."""
    error = _refusal(BareCoreEntity)

    assert error.entity_name == "BareCoreEntity"
    assert error.field_name == "showcase"
    assert "ShowcaseCoreEntity" in error.details
    assert "AssociationOne" in error.details
    assert "NoRelation" in error.details


def test_a_bare_optional_entity_field_is_refused() -> None:
    """`X | None` without a container is not a declaration either."""
    error = _refusal(OptionalBareCoreEntity)

    assert "showcase" in str(error)
    assert "NoRelation" in error.details


@pytest.mark.parametrize(
    "entity_cls",
    [ListCoreEntity, DictCoreEntity, SetCoreEntity, TupleCoreEntity],
)
def test_a_collection_of_entities_is_refused(entity_cls: type) -> None:
    """A container of an entity is not a relation; the many forms are named instead."""
    error = _refusal(entity_cls)

    assert error.field_name == "showcases"
    assert "AssociationMany" in error.details


def test_a_state_entity_field_names_the_lifecycle_form() -> None:
    """A state is neither a relation nor a plain field."""
    error = _refusal(StateFieldCoreEntity)

    assert error.field_name == "stage"
    assert "Lifecycle[...]" in error.details


def test_a_state_entity_inside_a_relation_container_is_refused() -> None:
    """Wrapping a state in a relation container does not give it a field form."""
    error = _refusal(StateRelationCoreEntity)

    assert "Lifecycle[...]" in error.details


def test_the_embedded_marker_does_not_apply_to_a_state() -> None:
    """The marker is for Core, Assoc, Detail and Spec only."""
    error = _refusal(StateMarkerCoreEntity)

    assert "Lifecycle[...]" in error.details


def test_the_embedded_marker_is_refused_on_a_dictionary() -> None:
    """A dictionary reference is already a bare type; the marker would be meaningless."""
    error = _refusal(MarkerOnEnumCoreEntity)

    assert "NoRelation" in error.details
    assert "CurrencyEnumEntity" in error.details


def test_the_embedded_marker_cannot_accompany_a_relation() -> None:
    """A field either has a relation or it does not."""
    error = _refusal(MarkerWithRelationCoreEntity)

    assert "cannot be combined" in error.details


def test_a_blank_marker_reason_is_refused_at_construction() -> None:
    """The reason is the point of the marker, so it is required."""
    with pytest.raises(ValueError, match="whitespace-only"):
        NoRelation("   ")


def test_a_forward_reference_is_judged_only_after_it_resolves() -> None:
    """An unresolved name is not evidence of a scalar: the rule waits, then judges the class."""
    validate_entity_fields([ForwardCoreEntity])

    ForwardCoreEntity.model_rebuild()
    error = _refusal(ForwardCoreEntity)

    assert "LaterCoreEntity" in error.details


def test_the_relation_form_builds_an_edge() -> None:
    """The first legal form: no refusal, and the graph gains the relation."""
    validate_entity_fields([RelationCoreEntity, ManyRelationCoreEntity])

    node = EntityGraphNode(RelationCoreEntity)
    targets = [edge.target_node_id for edge in node.relations]
    assert any("ShowcaseCoreEntity" in target for target in targets)


def test_the_embedded_form_stays_a_column() -> None:
    """The second legal form: no refusal, and no relation edge."""
    validate_entity_fields([EmbeddedCoreEntity])

    node = EntityGraphNode(EmbeddedCoreEntity)
    assert node.relations == []
    assert "showcase" in {edge.target_node.label for edge in node.entity_field_edges}


def test_untouched_forms_pass_unchanged() -> None:
    """A dictionary, a lifecycle, a schema type and an ordinary scalar are not the rule's business."""
    validate_entity_fields([OrdinaryCoreEntity])


def test_a_class_outside_the_graph_is_not_judged() -> None:
    """An excluded class cannot break a build it never joins."""
    assert BareCoreEntity not in declared_entity_classes()

    validate_entity_fields()

def test_the_graph_build_runs_the_field_pass(monkeypatch: pytest.MonkeyPatch) -> None:
    """The rule belongs to the build: a caller cannot publish a graph without it."""
    from aoa.action_machine.graph.core.node_graph_coordinator import NodeGraphCoordinator
    from aoa.action_machine.graph.validators import entity_field_validator as validator_module

    calls: list[bool] = []
    monkeypatch.setattr(
        validator_module, "validate_entity_fields", lambda entities=None: calls.append(True)
    )

    NodeGraphCoordinator().build([])

    assert calls == [True]

def test_a_required_relation_must_be_supplied() -> None:
    """The default contract, row one: no default at all."""
    validate_entity_fields([RequiredRelationCoreEntity])

    with pytest.raises(ValidationError):
        RequiredRelationCoreEntity()
    with pytest.raises(ValidationError):
        RequiredRelationCoreEntity(showcase=None)


def test_a_nullable_required_relation_still_must_be_supplied() -> None:
    """The default contract, row two: ``| None`` alone gives no default."""
    validate_entity_fields([NullableRequiredCoreEntity])

    with pytest.raises(ValidationError):
        NullableRequiredCoreEntity()
    assert NullableRequiredCoreEntity(showcase=None).showcase is None


def test_an_omittable_relation_yields_none() -> None:
    """The default contract, row three: a nullable relation with an explicit ``None``."""
    validate_entity_fields([OmittableCoreEntity])

    assert OmittableCoreEntity().showcase is None
    assert OmittableCoreEntity(showcase=None).showcase is None


def test_none_on_a_non_nullable_relation_is_refused_at_declaration() -> None:
    """The default contract, row four: ``default=None`` needs a nullable annotation."""
    error = _refusal(NonNullableDefaultCoreEntity)

    assert "showcase" in str(error)
    assert "None" in error.details


def test_a_prebuilt_relation_default_is_refused() -> None:
    """A value in the default slot is not a default the framework can honour."""
    error = _refusal(PrebuiltDefaultCoreEntity)

    assert "showcase" in str(error)


def test_a_factory_is_refused_and_never_executed() -> None:
    """Refusing a factory must not run user code."""
    _FACTORY_CALLS.clear()

    with pytest.raises(EntityFieldDeclarationError):
        validate_entity_fields([FactoryCoreEntity])

    assert _FACTORY_CALLS == []


@pytest.mark.parametrize(
    "entity_cls", [BlankDescriptionCoreEntity, MissingDescriptionCoreEntity, HiddenEdgeCoreEntity]
)
def test_a_relation_without_a_description_is_refused(entity_cls: type) -> None:
    """A missing, blank or whitespace-only description is refused, hidden edge or not."""
    error = _refusal(entity_cls)

    assert "description" in error.details


def test_both_field_syntaxes_feed_one_description() -> None:
    """The assignment wins over the inner ``Field``, and each alone is enough."""
    validate_entity_fields([InnerSyntaxCoreEntity, BothSyntaxesCoreEntity])

    inner = InnerSyntaxCoreEntity.model_fields["showcase"].description
    outer = BothSyntaxesCoreEntity.model_fields["showcase"].description
    assert inner == "Inner showcase"
    assert outer == "Outer showcase"


def test_an_inherited_relation_is_judged() -> None:
    """A relation declared on a base class obeys the same rules on the class that inherits it."""
    error = _refusal(InheritedRelationCoreEntity)

    assert error.field_name == "showcase"
