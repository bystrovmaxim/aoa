# tests2/bench/test_state_validator.py
"""
Tests for validate_state_for_aspect and validate_state_for_summary.

These functions check that a manually-provided state dict contains all required
fields (with correct types) before executing a single aspect or summary via
TestBench.run_aspect / run_summary. Validation uses checker metadata from
the GateCoordinator to detect missing or invalid fields early.

Scenarios covered:
    - Valid state for the second aspect passes without error.
    - Missing required field raises StateValidationError with field name.
    - Wrong field type raises StateValidationError with checker description.
    - First aspect has no preceding checkers — any state is valid.
    - Non-existent aspect name raises StateValidationError.
    - validate_state_for_summary checks fields from ALL regular aspects.
    - Summary with complete valid state passes without error.
    - Summary with missing field raises StateValidationError.
    - Optional (required=False) fields do not cause errors when absent.
"""

import pytest

from action_machine.core.gate_coordinator import GateCoordinator
from action_machine.testing.state_validator import (
    StateValidationError,
    validate_state_for_aspect,
    validate_state_for_summary,
)
from tests2.domain import FullAction, PingAction, SimpleAction

# ─────────────────────────────────────────────────────────────────────────────
# Shared fixture — coordinator with registered domain actions
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture()
def coordinator() -> GateCoordinator:
    """Fresh GateCoordinator that has scanned all domain actions."""
    return GateCoordinator()


# ═════════════════════════════════════════════════════════════════════════════
# validate_state_for_aspect
# ═════════════════════════════════════════════════════════════════════════════


class TestValidateForAspect:
    """Verify pre-aspect state validation against preceding checkers."""

    def test_valid_state_for_second_aspect(self, coordinator: GateCoordinator) -> None:
        """State with txn_id satisfies checkers preceding calc_total."""
        # Arrange — FullAction: process_payment → calc_total → summary
        # calc_total requires txn_id from process_payment
        metadata = coordinator.get(FullAction)
        state = {"txn_id": "TXN-001"}

        # Act — should not raise
        validate_state_for_aspect(metadata, "calc_total", state)

    def test_missing_required_field(self, coordinator: GateCoordinator) -> None:
        """Empty state before calc_total triggers error for missing txn_id."""
        metadata = coordinator.get(FullAction)

        with pytest.raises(StateValidationError, match="txn_id"):
            validate_state_for_aspect(metadata, "calc_total", {})

    def test_wrong_field_type(self, coordinator: GateCoordinator) -> None:
        """Non-string txn_id triggers checker validation error."""
        metadata = coordinator.get(FullAction)
        state = {"txn_id": 12345}

        with pytest.raises(StateValidationError, match="txn_id"):
            validate_state_for_aspect(metadata, "calc_total", state)

    def test_first_aspect_accepts_any_state(self, coordinator: GateCoordinator) -> None:
        """First aspect (process_payment) has no preceding checkers — any state is fine."""
        metadata = coordinator.get(FullAction)

        # Act — should not raise even with empty state
        validate_state_for_aspect(metadata, "process_payment", {})

    def test_nonexistent_aspect_raises(self, coordinator: GateCoordinator) -> None:
        """Unknown aspect name raises StateValidationError listing available aspects."""
        metadata = coordinator.get(FullAction)

        with pytest.raises(StateValidationError, match="не найден"):
            validate_state_for_aspect(metadata, "nonexistent_aspect", {})

    def test_single_aspect_action(self, coordinator: GateCoordinator) -> None:
        """SimpleAction has one regular aspect — validating it requires no preceding fields."""
        metadata = coordinator.get(SimpleAction)

        # validate_name is the only regular aspect — no predecessors
        validate_state_for_aspect(metadata, "validate_name", {})


# ═════════════════════════════════════════════════════════════════════════════
# validate_state_for_summary
# ═════════════════════════════════════════════════════════════════════════════


class TestValidateForSummary:
    """Verify pre-summary state validation against ALL regular aspect checkers."""

    def test_complete_state_passes(self, coordinator: GateCoordinator) -> None:
        """State with all required fields from both regular aspects passes."""
        metadata = coordinator.get(FullAction)
        state = {"txn_id": "TXN-001", "total": 1500.0}

        # Act — should not raise
        validate_state_for_summary(metadata, state)

    def test_missing_first_aspect_field(self, coordinator: GateCoordinator) -> None:
        """Missing txn_id (from process_payment) raises error before summary."""
        metadata = coordinator.get(FullAction)
        state = {"total": 1500.0}

        with pytest.raises(StateValidationError, match="txn_id"):
            validate_state_for_summary(metadata, state)

    def test_missing_second_aspect_field(self, coordinator: GateCoordinator) -> None:
        """Missing total (from calc_total) raises error before summary."""
        metadata = coordinator.get(FullAction)
        state = {"txn_id": "TXN-001"}

        with pytest.raises(StateValidationError, match="total"):
            validate_state_for_summary(metadata, state)

    def test_empty_state_raises(self, coordinator: GateCoordinator) -> None:
        """Completely empty state raises error for the first missing required field."""
        metadata = coordinator.get(FullAction)

        with pytest.raises(StateValidationError):
            validate_state_for_summary(metadata, {})

    def test_action_without_regular_aspects(self, coordinator: GateCoordinator) -> None:
        """PingAction has no regular aspects — any state is valid for summary."""
        metadata = coordinator.get(PingAction)

        # Act — should not raise
        validate_state_for_summary(metadata, {})

    def test_simple_action_summary(self, coordinator: GateCoordinator) -> None:
        """SimpleAction summary requires validated_name from validate_name aspect."""
        metadata = coordinator.get(SimpleAction)
        state = {"validated_name": "Alice"}

        # Act — should not raise
        validate_state_for_summary(metadata, state)

    def test_simple_action_summary_missing_field(self, coordinator: GateCoordinator) -> None:
        """SimpleAction summary with empty state raises for missing validated_name."""
        metadata = coordinator.get(SimpleAction)

        with pytest.raises(StateValidationError, match="validated_name"):
            validate_state_for_summary(metadata, {})


# ═════════════════════════════════════════════════════════════════════════════
# StateValidationError attributes
# ═════════════════════════════════════════════════════════════════════════════


class TestErrorAttributes:
    """Verify that StateValidationError carries structured metadata."""

    def test_field_attribute(self, coordinator: GateCoordinator) -> None:
        """The error's field attribute names the problematic field."""
        metadata = coordinator.get(FullAction)

        with pytest.raises(StateValidationError) as exc_info:
            validate_state_for_aspect(metadata, "calc_total", {})

        assert exc_info.value.field == "txn_id"

    def test_source_aspect_attribute(self, coordinator: GateCoordinator) -> None:
        """The error's source_aspect attribute names the aspect that should have written the field."""
        metadata = coordinator.get(FullAction)

        with pytest.raises(StateValidationError) as exc_info:
            validate_state_for_aspect(metadata, "calc_total", {})

        assert exc_info.value.source_aspect == "process_payment"

    def test_nonexistent_aspect_has_no_field(self, coordinator: GateCoordinator) -> None:
        """Error for non-existent aspect has field=None and source_aspect=None."""
        metadata = coordinator.get(FullAction)

        with pytest.raises(StateValidationError) as exc_info:
            validate_state_for_aspect(metadata, "no_such_aspect", {})

        assert exc_info.value.field is None
        assert exc_info.value.source_aspect is None
