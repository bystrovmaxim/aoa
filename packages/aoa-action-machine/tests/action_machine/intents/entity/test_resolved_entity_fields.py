# tests/action_machine/intents/entity/test_resolved_entity_fields.py
"""
Tests for ``resolved_entity_fields`` — the build-local normalized view of one field.

The descriptor reads ``FieldInfo.annotation`` and ``FieldInfo.metadata`` only; it never
re-runs ``get_type_hints``. These tests pin the classification, the direction-marker
count, the declaring-owner/effective-host split and the refusal of ambiguous unions.

Every fixture is a plain ``@exclude_graph_model`` class: the descriptor does not need
``@entity``, and the exclusion keeps the fixtures out of the global graph other tests build.
"""

from __future__ import annotations

from typing import Annotated

import pytest
from pydantic import Field

from aoa.action_machine.domain import (
    AssociationMany,
    AssociationOne,
    BaseCoreEntity,
    BaseDomain,
    BaseEnumEntity,
    BaseSpecEntity,
    CompositeOne,
    Generalization,
    Inverse,
    NoGraphEdge,
    NoInverse,
    NoRelation,
    Specialization,
    value,
)
from aoa.action_machine.domain.exceptions import EntityFieldDeclarationError
from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
from aoa.action_machine.intents.entity.resolved_entity_fields import (
    declaring_owner_of,
    is_generalization_container,
    is_relation_container,
    is_specialization_container,
    resolve_entity_field,
    resolve_entity_fields,
)


class ProbeDomain(BaseDomain):
    """Domain for descriptor fixtures."""

    name = "probe"
    description = "Probe domain"


@exclude_graph_model
class TargetCoreEntity(BaseCoreEntity):
    """A structural target."""

    id: str = "x"


@exclude_graph_model
class OtherCoreEntity(BaseCoreEntity):
    """A second structural target."""

    id: str = "x"


@exclude_graph_model
class CurrencyEnumEntity(BaseEnumEntity):
    """A dictionary."""

    EUR = value(code="eur", display_name="Euro")


@exclude_graph_model
class AltASpecEntity(BaseSpecEntity):
    """First specialization alternative."""

    id: str = "x"


@exclude_graph_model
class AltBSpecEntity(BaseSpecEntity):
    """Second specialization alternative."""

    id: str = "x"


@exclude_graph_model
class HostCoreEntity(BaseCoreEntity):
    """A host declaring every relation shape the descriptor classifies."""

    assoc: AssociationOne[TargetCoreEntity]
    optional: AssociationOne[TargetCoreEntity] | None = None
    many: AssociationMany[TargetCoreEntity]
    composite: CompositeOne[TargetCoreEntity]
    specialization: Specialization[AltASpecEntity | AltBSpecEntity, CurrencyEnumEntity]
    generalization: Generalization[TargetCoreEntity]
    bare: TargetCoreEntity
    scalar: str = "x"


def _field(host: type, name: str):
    return resolve_entity_field(host, name, host.model_fields[name])


def test_relation_container_resolves_target_by_identity() -> None:
    """A relation container resolves its target class from the annotation, by identity."""
    field = _field(HostCoreEntity, "assoc")

    assert field.is_relation
    assert field.relation_kind == "association"
    assert field.cardinality == "one"
    assert field.targets == (TargetCoreEntity,)
    assert field.targets[0] is TargetCoreEntity


def test_nullable_relation_is_still_one_container() -> None:
    """``AssociationOne[T] | None`` is one nullable relation, not an ambiguous union."""
    field = _field(HostCoreEntity, "optional")

    assert field.is_relation
    assert field.nullable
    assert field.cardinality == "one"
    assert field.targets == (TargetCoreEntity,)


def test_many_relation_reports_many_cardinality() -> None:
    """The cardinality follows the container, not the annotation's outer shape."""
    field = _field(HostCoreEntity, "many")

    assert field.cardinality == "many"
    assert field.relation_kind == "association"


def test_composition_kind_is_reported() -> None:
    """Composition keeps its ownership flavour in ``relation_kind``."""
    assert _field(HostCoreEntity, "composite").relation_kind == "composition"


def test_inverse_markers_come_from_field_metadata() -> None:
    """``Inverse`` is read from ``FieldInfo.metadata``, not from the annotation."""

    @exclude_graph_model
    class InversedCoreEntity(BaseCoreEntity):
        link: Annotated[AssociationOne[TargetCoreEntity], Inverse(TargetCoreEntity, "back")] = Field(description="Link")

    field = _field(InversedCoreEntity, "link")

    assert field.has_inverse
    assert field.inverse_entity is TargetCoreEntity
    assert field.inverse_field == "back"
    assert field.direction_marker_count == 1


def test_no_inverse_marker_counts_as_one_direction_marker() -> None:
    """``NoInverse`` is an explicit direction marker, so the count is one."""

    @exclude_graph_model
    class NoInverseCoreEntity(BaseCoreEntity):
        link: Annotated[AssociationOne[TargetCoreEntity], NoInverse()] = Field(description="Link")

    field = _field(NoInverseCoreEntity, "link")

    assert not field.has_inverse
    assert field.direction_marker_count == 1


def test_duplicate_direction_markers_are_counted_not_silently_merged() -> None:
    """Two direction markers are both preserved; the count is two, for the validator to refuse."""

    @exclude_graph_model
    class DuplicateCoreEntity(BaseCoreEntity):
        link: Annotated[
            AssociationOne[TargetCoreEntity],
            Inverse(TargetCoreEntity, "back"),
            NoInverse(),
        ] = Field(description="Link")

    field = _field(DuplicateCoreEntity, "link")

    assert field.direction_marker_count == 2


def test_specialization_reports_alternatives_and_dictionary() -> None:
    """The alternatives and the dictionary come from the resolved container arguments."""
    field = _field(HostCoreEntity, "specialization")

    assert field.is_specialization
    assert field.relation_kind == "specialization"
    assert field.targets == (AltASpecEntity, AltBSpecEntity)
    assert field.dictionary is CurrencyEnumEntity


def test_generalization_reports_head() -> None:
    """The head is the generalization container's single resolved target."""
    field = _field(HostCoreEntity, "generalization")

    assert field.is_generalization
    assert field.relation_kind == "generalization"
    assert field.cardinality == "one"
    assert field.targets == (TargetCoreEntity,)


def test_bare_entity_and_scalar_are_not_relations() -> None:
    """A bare entity and a scalar carry no container, kind or targets."""
    bare = _field(HostCoreEntity, "bare")
    scalar = _field(HostCoreEntity, "scalar")

    assert not bare.is_relation and bare.targets == () and bare.container is None
    assert not scalar.is_relation and scalar.targets == ()


def test_ambiguous_union_of_two_containers_is_refused() -> None:
    """A field that names two relation containers has no single meaning."""

    @exclude_graph_model
    class AmbiguousCoreEntity(BaseCoreEntity):
        link: Annotated[AssociationOne[TargetCoreEntity] | CompositeOne[OtherCoreEntity], NoInverse()] = Field(
            description="Link"
        )

    with pytest.raises(EntityFieldDeclarationError) as caught:
        resolve_entity_field(AmbiguousCoreEntity, "link", AmbiguousCoreEntity.model_fields["link"])

    assert "ambiguous union" in caught.value.details
    assert caught.value.field_name == "link"


def test_declaring_owner_is_base_for_unchanged_inheritance() -> None:
    """An unchanged inherited field keeps the base as its declaring owner."""

    @exclude_graph_model
    class BaseHostCoreEntity(BaseCoreEntity):
        link: AssociationOne[TargetCoreEntity] = "x"

    @exclude_graph_model
    class ChildHostCoreEntity(BaseHostCoreEntity):
        extra: str = "x"

    field = _field(ChildHostCoreEntity, "link")

    assert field.effective_host is ChildHostCoreEntity
    assert field.declaring_owner is BaseHostCoreEntity


def test_declaring_owner_is_child_for_target_changing_override() -> None:
    """An override that changes the resolved target owns the new endpoint."""

    @exclude_graph_model
    class BaseHostCoreEntity(BaseCoreEntity):
        link: AssociationOne[TargetCoreEntity] = "x"

    @exclude_graph_model
    class ChildHostCoreEntity(BaseHostCoreEntity):
        link: AssociationOne[OtherCoreEntity] = "x"

    field = _field(ChildHostCoreEntity, "link")

    assert field.declaring_owner is ChildHostCoreEntity
    assert field.targets == (OtherCoreEntity,)


def test_declaring_owner_through_two_levels_of_inheritance() -> None:
    """The owner is the class that first introduced the unchanged declaration."""

    @exclude_graph_model
    class RootHostCoreEntity(BaseCoreEntity):
        link: AssociationOne[TargetCoreEntity] = "x"

    @exclude_graph_model
    class MidHostCoreEntity(RootHostCoreEntity):
        extra: str = "x"

    @exclude_graph_model
    class LeafHostCoreEntity(MidHostCoreEntity):
        more: str = "x"

    assert declaring_owner_of(LeafHostCoreEntity, "link") is RootHostCoreEntity


@exclude_graph_model
class LaterCoreEntity(BaseCoreEntity):
    """The class an explicit namespace later resolves a forward reference to."""

    id: str = "x"


def test_forward_reference_resolves_via_explicit_namespace() -> None:
    """An unresolved forward reference has no target until an explicit namespace resolves it."""

    @exclude_graph_model
    class ForwardCoreEntity(BaseCoreEntity):
        link: AssociationOne[TheLaterTarget] = Field(description="Link")  # noqa: F821 - resolved by explicit namespace

    before = _field(ForwardCoreEntity, "link")
    assert before.targets == ()
    assert not before.is_relation

    ForwardCoreEntity.model_rebuild(_types_namespace={"TheLaterTarget": LaterCoreEntity})
    after = _field(ForwardCoreEntity, "link")
    assert after.targets == (LaterCoreEntity,)
    assert after.is_relation


def test_relation_flags_and_metadata_surface() -> None:
    """A relation field exposes description, default contract and NoGraphEdge/NoRelation."""

    @exclude_graph_model
    class SurfacedCoreEntity(BaseCoreEntity):
        link: Annotated[AssociationOne[TargetCoreEntity], NoInverse(), NoGraphEdge()] = Field(
            description="Link", default=None
        )

    field = _field(SurfacedCoreEntity, "link")

    assert field.description == "Link"
    assert field.omit_graph_edge
    assert not field.has_no_relation
    assert field.deprecated is False


def test_no_relation_marker_is_surfaced() -> None:
    """The embedded-value marker is exposed for the completeness validator to refuse."""

    @exclude_graph_model
    class EmbeddedCoreEntity(BaseCoreEntity):
        value: Annotated[TargetCoreEntity, NoRelation("embedded snapshot")] = Field(description="Value")

    field = _field(EmbeddedCoreEntity, "value")

    assert field.has_no_relation
    assert not field.is_relation


def test_container_classifiers_agree_with_resolved_fields() -> None:
    """The public predicate helpers classify each shape the descriptor classifies."""
    assert is_relation_container(AssociationOne[TargetCoreEntity])
    assert is_relation_container(AssociationOne[TargetCoreEntity] | None)
    assert is_specialization_container(Specialization[AltASpecEntity | AltBSpecEntity, CurrencyEnumEntity])
    assert is_generalization_container(Generalization[TargetCoreEntity])


def test_resolve_entity_fields_returns_field_order() -> None:
    """The descriptor list keeps the host's declared field order."""
    names = [field.field_name for field in resolve_entity_fields(HostCoreEntity)]

    assert names == [
        "assoc",
        "optional",
        "many",
        "composite",
        "specialization",
        "generalization",
        "bare",
        "scalar",
    ]
