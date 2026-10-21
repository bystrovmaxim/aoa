# tests/action_machine/domain/test_state_entity.py
"""
Tests for `BaseStateEntity` and the `StateVocabulary` mixin.

Covers the status object's fields and refusals, the mixin's collection and
checks at class creation, the inherited axis, the plain-methods API, and the
status type never appearing as an entity of the model graph.
"""

from __future__ import annotations

import pytest
from pydantic import Field, ValidationError

from aoa.action_machine.domain import BaseStateEntity, Lifecycle, StateVocabulary
from aoa.action_machine.graph.core.exclude_graph_model import excluded_from_graph_model
from aoa.action_machine.graph.inspectors.entity_graph_node_inspector import EntityGraphNodeInspector


class SampleStateEntity(BaseStateEntity):
    """Status used by the tests."""

    sort_order: int = Field(default=0, description="Presentation order")


class AlternateStateEntity(BaseStateEntity):
    """A second status type, used to prove the mixed-type refusal."""

    reason: str = Field(default="", description="Refund reason")


FOREIGN = AlternateStateEntity(code="foreign", display_name="Foreign")


class SampleLifecycle(Lifecycle, StateVocabulary):
    """The axis the tests read."""

    NEW = SampleStateEntity(code="new", display_name="New", sort_order=1)
    PAID = SampleStateEntity(code="paid", display_name="Paid", sort_order=2)
    CANCELLED = SampleStateEntity(code="cancelled", display_name="Cancelled", sort_order=3)

    _template = (
        Lifecycle()
        .state(NEW).to(PAID, CANCELLED).initial()
        .state(PAID).to(CANCELLED).intermediate()
        .state(CANCELLED).final()
    )


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


class TestVocabulary:
    """The mixin's collection, lookup and checks."""

    def test_members_in_declaration_order(self):
        assert [member.code for member in SampleLifecycle.members] == ["new", "paid", "cancelled"]

    def test_codes_and_lookup(self):
        assert SampleLifecycle.codes() == ["new", "paid", "cancelled"]
        assert SampleLifecycle.by_code("paid") is SampleLifecycle.PAID
        with pytest.raises(KeyError):
            SampleLifecycle.by_code("missing")

    def test_shared_status_type(self):
        assert SampleLifecycle.entity_type is SampleStateEntity

    def test_api_is_plain_methods(self):
        instance = SampleLifecycle("new")
        assert not hasattr(SampleLifecycle, "__len__")
        assert not hasattr(instance, "__iter__")
        assert not hasattr(instance, "__contains__")

    def test_duplicate_code_is_refused(self):
        with pytest.raises(ValueError, match="duplicate status code"):

            class DuplicateAxis(Lifecycle, StateVocabulary):
                A = SampleStateEntity(code="same", display_name="A")
                B = SampleStateEntity(code="same", display_name="B")
                _template = Lifecycle().state(A).initial()

    def test_mixed_types_are_refused(self):
        with pytest.raises(TypeError, match="different types"):

            class MixedAxis(Lifecycle, StateVocabulary):
                A = SampleStateEntity(code="a", display_name="A")
                B = AlternateStateEntity(code="b", display_name="B")
                _template = Lifecycle().state(A).initial()

    def test_axis_without_statuses_is_refused(self):
        with pytest.raises(ValueError, match="at least one status"):

            class EmptyAxis(Lifecycle, StateVocabulary):
                _template = Lifecycle().state(FOREIGN).initial()

    def test_mixin_without_lifecycle_is_refused(self):
        with pytest.raises(TypeError, match="Lifecycle subclass"):

            class NotAnAxis(StateVocabulary):
                pass

    def test_foreign_status_in_template_is_refused(self):
        with pytest.raises(TypeError, match="is not a status of this lifecycle"):

            class ForeignAxis(Lifecycle, StateVocabulary):
                A = SampleStateEntity(code="a", display_name="A")
                _template = Lifecycle().state(A).to(FOREIGN).initial()

    def test_subclass_inherits_members(self):
        class SpecializedSampleLifecycle(SampleLifecycle):
            pass

        assert SpecializedSampleLifecycle.members == SampleLifecycle.members
        assert SpecializedSampleLifecycle.by_code("paid") is SampleLifecycle.PAID
        assert SpecializedSampleLifecycle("paid").current_state == "paid"
