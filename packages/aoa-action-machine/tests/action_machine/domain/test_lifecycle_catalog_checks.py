# packages/aoa-action-machine/tests/action_machine/domain/test_lifecycle_catalog_checks.py
"""The axis refuses a foreign status and a missing status at class creation."""

from __future__ import annotations

import pytest

from aoa.action_machine.domain import BaseStateEntity, ForeignStateError, Lifecycle, MissingStateError, value


class CheckStateEntity(BaseStateEntity):
    """Status type used by the refusal tests."""

    DRAFT = value(code="draft", display_name="Draft")
    PAID = value(code="paid", display_name="Paid")
    CANCELLED = value(code="cancelled", display_name="Cancelled")


class OtherStateEntity(BaseStateEntity):
    """A second status type, to be refused by the first axis."""

    GHOST = value(code="ghost", display_name="Ghost")


class EmptyCheckStateEntity(BaseStateEntity):
    """A state type with no statuses."""


class CheckLifecycle(Lifecycle[CheckStateEntity]):
    """A complete axis over ``CheckStateEntity``."""

    _template = (
        Lifecycle()
        .state(CheckStateEntity.DRAFT).to(CheckStateEntity.PAID).initial()
        .state(CheckStateEntity.PAID).to(CheckStateEntity.CANCELLED).intermediate()
        .state(CheckStateEntity.CANCELLED).final()
    )


def test_a_complete_axis_builds_and_names_its_type():
    """Resolve the state type and keep every declared status."""
    assert CheckLifecycle._state_type is CheckStateEntity
    assert CheckLifecycle("draft").current_state == "draft"


def test_a_status_of_another_type_is_refused():
    """Refuse a status object that is not a member of the axis's type."""
    with pytest.raises(ForeignStateError, match="is not a declared status"):

        class ForeignChecksLifecycle(Lifecycle[CheckStateEntity]):
            _template = (
                Lifecycle()
                .state(CheckStateEntity.DRAFT).to(OtherStateEntity.GHOST).initial()
                .state(CheckStateEntity.PAID).final()
                .state(CheckStateEntity.CANCELLED).final()
            )


def test_an_equal_but_distinct_instance_is_refused():
    """Refuse a twin that compares equal to a declared status but is not it."""
    twin = CheckStateEntity(code="draft", display_name="Draft")
    with pytest.raises(ForeignStateError, match="different instance"):

        class TwinChecksLifecycle(Lifecycle[CheckStateEntity]):
            _template = (
                Lifecycle()
                .state(twin).to(CheckStateEntity.PAID).initial()
                .state(CheckStateEntity.PAID).to(CheckStateEntity.CANCELLED).intermediate()
                .state(CheckStateEntity.CANCELLED).final()
            )


def test_a_missing_status_is_refused():
    """Refuse an axis that leaves a declared status out of its states."""
    with pytest.raises(MissingStateError, match="cancelled"):

        class MissingChecksLifecycle(Lifecycle[CheckStateEntity]):
            _template = (
                Lifecycle()
                .state(CheckStateEntity.DRAFT).to(CheckStateEntity.PAID).initial()
                .state(CheckStateEntity.PAID).final()
            )


def test_a_target_only_status_is_still_missing():
    """A declared status used only in ``.to(...)`` is not a state."""
    with pytest.raises(MissingStateError, match="paid"):

        class TargetOnlyChecksLifecycle(Lifecycle[CheckStateEntity]):
            _template = Lifecycle().state(CheckStateEntity.DRAFT).to(CheckStateEntity.PAID).initial()


def test_an_empty_catalogue_is_refused_when_the_template_has_states():
    """A state type with no statuses cannot satisfy a non-empty template."""
    with pytest.raises(ForeignStateError, match="declares no statuses"):

        class EmptyChecksLifecycle(Lifecycle[EmptyCheckStateEntity]):
            _template = Lifecycle().state(CheckStateEntity.DRAFT).initial()


def test_a_plain_lifecycle_is_unchecked():
    """A Lifecycle without a type parameter keeps today's behaviour."""

    class PlainChecksLifecycle(Lifecycle):
        _template = Lifecycle().state(CheckStateEntity.DRAFT).to(CheckStateEntity.PAID).initial()

    assert isinstance(PlainChecksLifecycle("draft"), Lifecycle)
