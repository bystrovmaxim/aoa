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

from aoa.action_machine.domain.lifecycle import (
    InvalidStateError,
    InvalidTransitionError,
    Lifecycle,
    StateType,
)


class TestLifecycleTemplate:
    """Template `Lifecycle` (fluent chain)."""

    def test_create_empty_lifecycle(self):
        """Empty template has no states."""
        lifecycle = Lifecycle()
        assert len(lifecycle._states) == 0

    def test_add_state(self):
        """Add a state via the fluent API."""
        lifecycle = Lifecycle().state("draft", "Draft").initial()
        assert len(lifecycle._states) == 1
        assert "draft" in lifecycle._states

    def test_state_properties(self):
        """State metadata: key, display name, type flags."""
        lifecycle = Lifecycle().state("draft", "Draft").initial()
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
            .state("draft", "Draft").to("active").initial()
            .state("active", "Active").to("archived").intermediate()
            .state("archived", "Archived").final()
        )
        assert len(lifecycle._states) == 3
        assert lifecycle._states["draft"].state_type == StateType.INITIAL
        assert lifecycle._states["active"].state_type == StateType.INTERMEDIATE
        assert lifecycle._states["archived"].state_type == StateType.FINAL

    def test_transitions(self):
        """Transition graph on the template."""
        lifecycle = (
            Lifecycle()
            .state("draft", "Draft").to("active", "cancelled").initial()
            .state("active", "Active").to("archived").intermediate()
            .state("archived", "Archived").final()
            .state("cancelled", "Cancelled").final()
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
            .state("new", "New").to("active").initial()
            .state("imported", "Imported").to("active").initial()
            .state("active", "Active").final()
        )
        assert lifecycle.get_initial_keys() == {"new", "imported"}

    def test_get_final_keys(self):
        """Collect final state keys."""
        lifecycle = (
            Lifecycle()
            .state("draft", "Draft").to("done", "cancelled").initial()
            .state("done", "Done").final()
            .state("cancelled", "Cancelled").final()
        )
        assert lifecycle.get_final_keys() == {"done", "cancelled"}

    def test_has_state(self):
        """`has_state` reflects declared keys."""
        lifecycle = Lifecycle().state("draft", "Draft").initial()
        assert lifecycle.has_state("draft")
        assert not lifecycle.has_state("nonexistent")

    def test_final_state_with_transitions_raises(self):
        """Final state must not declare outgoing transitions."""
        with pytest.raises(ValueError, match="cannot have outgoing"):
            Lifecycle().state("done", "Done").to("other").final()

    def test_duplicate_state_raises(self):
        """Duplicate state key is rejected."""
        with pytest.raises(ValueError, match="already defined"):
            (
                Lifecycle()
                .state("draft", "Draft").initial()
                .state("draft", "Duplicate").initial()
            )

    def test_uncompleted_state_raises(self):
        """Starting a new state before finalizing the previous one fails."""
        lc = Lifecycle()
        lc.state("draft", "Draft")
        with pytest.raises(RuntimeError, match="not complete"):
            lc.state("active", "Active")

    def test_double_finalize_raises(self):
        """Calling initial/intermediate/final twice on the same builder fails."""
        builder = Lifecycle().state("draft", "Draft")
        builder.initial()
        with pytest.raises(RuntimeError, match="already complete"):
            builder.initial()


class TestSpecializedLifecycle:
    """Specialized `Lifecycle` subclasses with `_template`."""

    def setup_method(self):
        class TestLC(Lifecycle):
            _template = (
                Lifecycle()
                .state("draft", "Draft").to("active").initial()
                .state("active", "Active").to("archived").intermediate()
                .state("archived", "Archived").final()
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
