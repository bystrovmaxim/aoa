"""Tests for :class:`~aoa.maxitor.model.diagrams.actions.get_lifecycle_finite_automaton_action.GetLifecycleFiniteAutomatonAction`."""

from __future__ import annotations

import pytest

from aoa.maxitor.model.diagrams.actions.get_lifecycle_finite_automaton_action import _parse_lifecycle_interchange_id


def test_parse_rejects_non_interchange_id() -> None:
    with pytest.raises(ValueError, match=":lifecycle:"):
        _parse_lifecycle_interchange_id("not-a-lifecycle-id")
