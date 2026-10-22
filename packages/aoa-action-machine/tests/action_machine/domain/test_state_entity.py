# tests/action_machine/domain/test_state_entity.py
# ruff: noqa: F821  # the class-name alias is the surface this module tests
"""
Tests for `BaseStateEntity`, its status catalogue and the graph exclusion.

Covers the status object's fields and refusals, the declaration surface, the
catalogue and its inheritance, and the status type never appearing as an entity
of the model graph.
"""

from __future__ import annotations

from typing import Any, ClassVar

import pytest
from pydantic import ConfigDict, Field, ValidationError
from pydantic.errors import PydanticUserError

from aoa.action_machine.domain import BaseStateEntity
from aoa.action_machine.domain.declared_values import value as state
from aoa.action_machine.graph.core.exclude_graph_model import excluded_from_graph_model
from aoa.action_machine.graph.inspectors.entity_graph_node_inspector import EntityGraphNodeInspector


class SampleStateEntity(BaseStateEntity):
    """Status used by the tests."""

    sort_order: int = Field(default=0, description="Presentation order")

    NEW = SampleStateEntity(code="new", display_name="New", sort_order=1)
    PAID = SampleStateEntity(code="paid", display_name="Paid", sort_order=2)
    CANCELLED = SampleStateEntity(code="cancelled", display_name="Cancelled", sort_order=3)



class CatalogueStateEntity(BaseStateEntity):
    """A state type that declares its own statuses and catalogue."""

    sort_order: int = Field(default=0, description="Presentation order")
    color: str = Field(default="#9e9e9e", description="Diagram colour")
    requires_receipt: bool = Field(default=False, description="Whether a receipt is needed")

    DRAFT = CatalogueStateEntity(code="draft", display_name="Draft", sort_order=99)
    PAID = CatalogueStateEntity(code="paid", display_name="Paid", sort_order=1, requires_receipt=True)
    CANCELLED = CatalogueStateEntity(code="cancelled", display_name="Cancelled", sort_order=2)


class EmptyCatalogueStateEntity(BaseStateEntity):
    """A state type that declares no statuses."""


class InheritedCatalogueStateEntity(CatalogueStateEntity):
    """A subclass that inherits the parent's catalogue."""


class ExtendedCatalogueStateEntity(CatalogueStateEntity):
    """A subclass that declares its own status."""

    EXTRA = ExtendedCatalogueStateEntity(code="extra", display_name="Extra")


class TestStateEntity:
    """The status object itself."""

    def test_fields_are_readable(self):
        state = SampleStateEntity(code="new", display_name="New", sort_order=7)
        assert (state.code, state.display_name, state.sort_order) == ("new", "New", 7)

    def test_blank_code_is_refused(self):
        with pytest.raises(ValidationError, match="cannot be empty"):
            SampleStateEntity(code="  ", display_name="New")

    def test_blank_label_is_refused(self):
        with pytest.raises(ValidationError, match="cannot be empty"):
            SampleStateEntity(code="new", display_name="")

    def test_required_fields(self):
        with pytest.raises(ValidationError):
            SampleStateEntity(display_name="New")  # type: ignore[call-arg]

    def test_extra_field_is_forbidden(self):
        with pytest.raises(ValidationError):
            SampleStateEntity(code="new", display_name="New", unknown=1)  # type: ignore[call-arg]

    def test_immutable(self):
        state = SampleStateEntity(code="new", display_name="New")
        with pytest.raises(ValidationError):
            state.code = "other"

    def test_never_a_model_entity(self):
        assert excluded_from_graph_model(BaseStateEntity)
        assert excluded_from_graph_model(SampleStateEntity)
        nodes = EntityGraphNodeInspector().get_graph_nodes()
        assert all(node.node_obj is not SampleStateEntity for node in nodes)


class TestStateTypeCatalogue:
    """The state type declares its own statuses and exposes their catalogue."""

    def test_every_field_is_initialised(self):
        draft = CatalogueStateEntity.DRAFT
        assert draft.model_dump() == {
            "code": "draft",
            "display_name": "Draft",
            "sort_order": 99,
            "color": "#9e9e9e",
            "requires_receipt": False,
        }
        assert CatalogueStateEntity.PAID.requires_receipt is True

    def test_omitted_fields_take_defaults(self):
        assert CatalogueStateEntity.CANCELLED.color == "#9e9e9e"
        assert CatalogueStateEntity.CANCELLED.requires_receipt is False

    def test_members_order_codes_and_lookup(self):
        assert [member.code for member in CatalogueStateEntity.members] == ["draft", "paid", "cancelled"]
        assert CatalogueStateEntity.codes() == ["draft", "paid", "cancelled"]
        assert CatalogueStateEntity.by_code("paid") is CatalogueStateEntity.PAID
        with pytest.raises(KeyError):
            CatalogueStateEntity.by_code("missing")
        assert CatalogueStateEntity.entity_type is CatalogueStateEntity

    def test_misspelled_field_is_refused(self):
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):

            class BrokenStateEntity(BaseStateEntity):
                sort_order: int = Field(default=0)
                DRAFT = BrokenStateEntity(code="draft", display_name="Draft", sort_ordr=1)

    def test_missing_required_field_is_refused(self):
        with pytest.raises(ValidationError, match="Field required"):

            class IncompleteStateEntity(BaseStateEntity):
                DRAFT = IncompleteStateEntity(display_name="Draft")

    def test_wrong_type_is_refused(self):
        with pytest.raises(ValidationError, match="valid integer"):

            class WrongTypeStateEntity(BaseStateEntity):
                sort_order: int = Field(default=0)
                DRAFT = WrongTypeStateEntity(code="draft", display_name="Draft", sort_order="abc")

    def test_coercible_value_is_stored_by_pydantic(self):
        class CoercedStateEntity(BaseStateEntity):
            sort_order: int = Field(default=0)
            DRAFT = CoercedStateEntity(code="draft", display_name="Draft", sort_order="42")

        assert CoercedStateEntity.DRAFT.sort_order == 42

    def test_duplicate_code_is_refused(self):
        with pytest.raises(ValueError, match="duplicate status code"):

            class DuplicateStateEntity(BaseStateEntity):
                A = DuplicateStateEntity(code="same", display_name="A")
                B = DuplicateStateEntity(code="same", display_name="B")

    def test_empty_catalogue_is_valid(self):
        assert EmptyCatalogueStateEntity.members == ()
        assert EmptyCatalogueStateEntity.codes() == []
        assert EmptyCatalogueStateEntity.entity_type is EmptyCatalogueStateEntity

    def test_subclass_without_statuses_inherits(self):
        assert InheritedCatalogueStateEntity.members == CatalogueStateEntity.members
        assert InheritedCatalogueStateEntity.by_code("paid") is CatalogueStateEntity.PAID
        assert InheritedCatalogueStateEntity.entity_type is InheritedCatalogueStateEntity

    def test_subclass_with_statuses_gets_its_own_catalogue(self):
        assert ExtendedCatalogueStateEntity.codes() == ["extra"]
        assert ExtendedCatalogueStateEntity.by_code("extra") is ExtendedCatalogueStateEntity.EXTRA
        assert ExtendedCatalogueStateEntity.entity_type is ExtendedCatalogueStateEntity

    def test_the_alias_is_only_the_call(self):
        class AliasStateEntity(BaseStateEntity):
            ALIAS: ClassVar[Any] = AliasStateEntity

        assert AliasStateEntity.ALIAS is state

    def test_an_unknown_name_still_raises_name_error(self):
        with pytest.raises(NameError):

            class UnknownStateEntity(BaseStateEntity):
                X = MISSING

    def test_a_global_with_the_same_name_is_shadowed(self):
        shadowed_state_entity = object()

        class ShadowedStateEntity(BaseStateEntity):
            DRAFT = ShadowedStateEntity(code="draft", display_name="Draft")

        assert ShadowedStateEntity is not shadowed_state_entity
        assert ShadowedStateEntity.DRAFT.code == "draft"

    def test_removing_ignored_types_fails_class_creation(self):
        with pytest.raises(PydanticUserError):

            class UnignoredStateEntity(BaseStateEntity):
                model_config = ConfigDict(ignored_types=())
                DRAFT = UnignoredStateEntity(code="draft", display_name="Draft")
