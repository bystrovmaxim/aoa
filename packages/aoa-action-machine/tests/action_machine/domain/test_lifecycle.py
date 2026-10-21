# tests/domain/test_lifecycle.py
"""
Tests for `Lifecycle` — declarative finite-state machines for entities.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Covers template construction (fluent API), `StateType`, specialized
`_template` subclasses, instance transitions, and failure paths.

═══════════════════════════════════════════════════════════════════════════════
TERMINOLOGY
═══════════════════════════════════════════════════════════════════════════════

**Template** — fluent `Lifecycle()` chain defining states and transitions.
**Instance** — frozen value object with `current_state` and `transition()`.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- **InvalidStateError** — unknown state key on an instance.
- **InvalidTransitionError** — disallowed transition for current state.

Coordinator-level lifecycle integrity validation is tested elsewhere.
"""

import pytest
from pydantic import Field

from aoa.action_machine.domain.lifecycle import InvalidStateError, InvalidTransitionError, Lifecycle, StateType
from aoa.action_machine.domain.state_entity import BaseStateEntity


class AxisStateEntity(BaseStateEntity):
    """Status used by the lifecycle tests."""

    order: int = Field(default=0, description="Presentation order")


def status(code: str, display_name: str | None = None) -> AxisStateEntity:
    """Build a status object for a test template; the code is the fallback label."""
    return AxisStateEntity(code=code, display_name=display_name or code)


class TestLifecycleTemplate:
    """Template `Lifecycle` (fluent chain)."""

    def test_create_empty_lifecycle(self):
        """Empty template has no states."""
        lifecycle = Lifecycle()
        assert len(lifecycle._states) == 0

    def test_add_state(self):
        """Add a state via the fluent API."""
        lifecycle = Lifecycle().state(status("draft", "Draft")).initial()
        assert len(lifecycle._states) == 1
        assert "draft" in lifecycle._states

    def test_state_properties(self):
        """State metadata: key, display name, type flags."""
        lifecycle = Lifecycle().state(status("draft", "Draft")).initial()
        state = lifecycle._states["draft"]
        assert state.key == "draft"
        assert state.display_name == "Draft"
        assert state.state_type == StateType.INITIAL
        assert state.is_initial
        assert not state.is_final
        assert not state.is_intermediate

    def test_multiple_states(self):
        """Several states with different classifications."""
        lifecycle = (
            Lifecycle()
            .state(status("draft", "Draft"))
            .to(status("active"))
            .initial()
            .state(status("active", "Active"))
            .to(status("archived"))
            .intermediate()
            .state(status("archived", "Archived"))
            .final()
        )
        assert len(lifecycle._states) == 3
        assert lifecycle._states["draft"].state_type == StateType.INITIAL
        assert lifecycle._states["active"].state_type == StateType.INTERMEDIATE
        assert lifecycle._states["archived"].state_type == StateType.FINAL

    def test_transitions(self):
        """Transition graph on the template."""
        lifecycle = (
            Lifecycle()
            .state(status("draft", "Draft"))
            .to(status("active"), status("cancelled"))
            .initial()
            .state(status("active", "Active"))
            .to(status("archived"))
            .intermediate()
            .state(status("archived", "Archived"))
            .final()
            .state(status("cancelled", "Cancelled"))
            .final()
        )
        transitions = lifecycle.get_transitions()
        assert transitions["draft"] == {"active", "cancelled"}
        assert transitions["active"] == {"archived"}
        assert transitions["archived"] == set()
        assert transitions["cancelled"] == set()

    def test_get_initial_keys(self):
        """Collect initial state keys."""
        lifecycle = (
            Lifecycle()
            .state(status("new", "New"))
            .to(status("active"))
            .initial()
            .state(status("imported", "Imported"))
            .to(status("active"))
            .initial()
            .state(status("active", "Active"))
            .final()
        )
        assert lifecycle.get_initial_keys() == {"new", "imported"}

    def test_get_final_keys(self):
        """Collect final state keys."""
        lifecycle = (
            Lifecycle()
            .state(status("draft", "Draft"))
            .to(status("done"), status("cancelled"))
            .initial()
            .state(status("done", "Done"))
            .final()
            .state(status("cancelled", "Cancelled"))
            .final()
        )
        assert lifecycle.get_final_keys() == {"done", "cancelled"}

    def test_has_state(self):
        """`has_state` reflects declared keys."""
        lifecycle = Lifecycle().state(status("draft", "Draft")).initial()
        assert lifecycle.has_state("draft")
        assert not lifecycle.has_state("nonexistent")

    def test_final_state_with_transitions_raises(self):
        """Final state must not declare outgoing transitions."""
        with pytest.raises(ValueError, match="cannot have outgoing"):
            Lifecycle().state(status("done", "Done")).to(status("other")).final()

    def test_duplicate_state_raises(self):
        """Duplicate state key is rejected."""
        with pytest.raises(ValueError, match="already defined"):
            (Lifecycle().state(status("draft", "Draft")).initial().state(status("draft", "Duplicate")).initial())

    def test_uncompleted_state_raises(self):
        """Starting a new state before finalizing the previous one fails."""
        lc = Lifecycle()
        lc.state(status("draft", "Draft"))
        with pytest.raises(RuntimeError, match="not complete"):
            lc.state(status("active", "Active"))

    def test_double_finalize_raises(self):
        """Calling initial/intermediate/final twice on the same builder fails."""
        builder = Lifecycle().state(status("draft", "Draft"))
        builder.initial()
        with pytest.raises(RuntimeError, match="already complete"):
            builder.initial()


    def test_string_state_is_refused(self):
        """The string form is gone: a bare key is not a status object."""
        with pytest.raises(TypeError):
            Lifecycle().state("draft")  # type: ignore[arg-type]

    def test_string_state_with_label_is_refused(self):
        """The old two-argument call no longer exists."""
        with pytest.raises(TypeError):
            Lifecycle().state("draft", "Draft")  # type: ignore[call-arg]

    def test_string_transition_is_refused(self):
        """A transition target must be a status object."""
        lifecycle = Lifecycle().state(status("draft", "Draft"))
        with pytest.raises(TypeError):
            lifecycle.to("active")  # type: ignore[arg-type]

    def test_label_override_is_refused(self):
        """A status carries its own label; a second one is refused."""
        with pytest.raises(TypeError):
            Lifecycle().state(status("draft", "Draft"), "Override")  # type: ignore[call-arg]


class TestSpecializedLifecycle:
    """Specialized `Lifecycle` subclasses with `_template`."""

    def setup_method(self):
        class TestLC(Lifecycle):
            _template = (
                Lifecycle()
                .state(status("draft", "Draft"))
                .to(status("active"))
                .initial()
                .state(status("active", "Active"))
                .to(status("archived"))
                .intermediate()
                .state(status("archived", "Archived"))
                .final()
            )

        self.TestLC = TestLC

    def test_create_instance(self):
        """Construct instance with current state key."""
        lc = self.TestLC("draft")
        assert lc.current_state == "draft"

    def test_invalid_state_raises(self):
        """Unknown state key at construction time."""
        with pytest.raises(InvalidStateError, match="not defined"):
            self.TestLC("nonexistent")

    def test_is_initial(self):
        assert self.TestLC("draft").is_initial
        assert not self.TestLC("draft").is_final

    def test_is_final(self):
        lc = self.TestLC("archived")
        assert lc.is_final
        assert not lc.is_initial

    def test_available_transitions(self):
        lc = self.TestLC("draft")
        assert lc.available_transitions == {"active"}

    def test_can_transition(self):
        lc = self.TestLC("draft")
        assert lc.can_transition("active")
        assert not lc.can_transition("archived")

    def test_transition(self):
        """`transition` returns a new instance; original unchanged."""
        lc = self.TestLC("draft")
        new_lc = lc.transition("active")

        assert new_lc.current_state == "active"
        assert lc.current_state == "draft"
        assert type(new_lc) is self.TestLC

    def test_invalid_transition_raises(self):
        with pytest.raises(InvalidTransitionError, match="not allowed"):
            self.TestLC("draft").transition("archived")

    def test_final_state_no_transitions(self):
        lc = self.TestLC("archived")
        assert lc.available_transitions == set()

    def test_template_access(self):
        template = self.TestLC._get_template()
        assert template is not None
        assert len(template.get_states()) == 3
        assert template.get_initial_keys() == {"draft"}
        assert template.get_final_keys() == {"archived"}

    def test_equality(self):
        lc1 = self.TestLC("draft")
        lc2 = self.TestLC("draft")
        assert lc1 == lc2

    def test_inequality(self):
        lc1 = self.TestLC("draft")
        lc2 = self.TestLC("active")
        assert lc1 != lc2

    def test_hash(self):
        lc1 = self.TestLC("draft")
        lc2 = self.TestLC("draft")
        assert hash(lc1) == hash(lc2)


# ═══════════════════════════════════════════════════════════════════════════════
# Entity form: the same template built from status objects
# ═══════════════════════════════════════════════════════════════════════════════


class AxisStateEntity(BaseStateEntity):
    """Status used by the entity-form tests."""

    order: int = Field(default=0, description="Presentation order")


class _EntityBuiltLifecycle(Lifecycle):
    """Entity-built twin of the string-built chain below."""

    NEW = AxisStateEntity(code="new", display_name="New", order=1)
    PAID = AxisStateEntity(code="paid", display_name="Paid", order=2)
    CANCELLED = AxisStateEntity(code="cancelled", display_name="Cancelled", order=3)

    _template = (
        Lifecycle()
        .state(NEW).to(PAID, CANCELLED).initial()
        .state(PAID).to(CANCELLED).intermediate()
        .state(CANCELLED).final()
    )


class _ForwardRefLifecycle(Lifecycle):
    """Transitions may name a status declared later in the same template."""

    FIRST = AxisStateEntity(code="first", display_name="First")
    SECOND = AxisStateEntity(code="second", display_name="Second")

    _template = (
        Lifecycle()
        .state(FIRST).to(SECOND).initial()
        .state(SECOND).final()
    )


_SHARED = AxisStateEntity(code="shared", display_name="Shared")
_NEXT = AxisStateEntity(code="next", display_name="Next")


class _SharedFinalChain(Lifecycle):
    """The shared status is final here."""

    _template = Lifecycle().state(_SHARED).final()


class _SharedIntermediateChain(Lifecycle):
    """The same status is intermediate here."""

    _template = (
        Lifecycle()
        .state(_SHARED).to(_NEXT).intermediate()
        .state(_NEXT).final()
    )


class TestEntityForm:
    """The entity form produces the same metadata and keeps the runtime."""

    def test_state_metadata_is_built_from_the_objects(self):
        """Keys, labels, classification and transitions come from the objects."""
        states = _EntityBuiltLifecycle._get_template().get_states()
        assert list(states) == ["new", "paid", "cancelled"]
        assert states["paid"].display_name == "Paid"
        assert states["paid"].transitions == frozenset({"cancelled"})
        assert states["cancelled"].is_final

    def test_objects_are_stored_on_the_template(self):
        template = _EntityBuiltLifecycle._get_template()
        assert template.get_state_entity("new") is _EntityBuiltLifecycle.NEW
        assert set(template.get_state_entities()) == {"new", "paid", "cancelled"}

    def test_objects_are_copied_to_instances(self):
        instance = _EntityBuiltLifecycle("paid")
        assert instance.get_state_entity("paid") is _EntityBuiltLifecycle.PAID

    def test_runtime_is_unchanged(self):
        instance = _EntityBuiltLifecycle("new")
        assert instance.current_state == "new"
        assert instance.can_transition("paid")
        assert not _EntityBuiltLifecycle("paid").can_transition("new")
        assert instance.transition("paid").current_state == "paid"

    def test_forward_reference_to_a_later_state(self):
        assert _ForwardRefLifecycle("first").can_transition("second")
        assert _ForwardRefLifecycle._get_template().get_final_keys() == {"second"}

    def test_same_status_classified_differently_by_two_chains(self):
        assert _SharedFinalChain._get_template().get_final_keys() == {"shared"}
        intermediate = _SharedIntermediateChain._get_template().get_states()["shared"]
        assert intermediate.state_type is StateType.INTERMEDIATE
