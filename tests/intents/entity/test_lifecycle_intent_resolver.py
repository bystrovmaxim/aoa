# tests/intents/entity/test_lifecycle_intent_resolver.py
"""Tests for :class:`LifeCycleIntentResolver`."""

from __future__ import annotations

from types import MappingProxyType

import pytest
from tests.scenarios.domain_model.entities import DraftLifecycle, LifecycleEntity, RelatedEntity

from action_machine.domain.lifecycle import StateType
from action_machine.intents.entity.lifecycle_intent_resolver import LifeCycleIntentResolver
from action_machine.legacy.entity_intent_inspector import collect_entity_lifecycles


def test_resolve_lifecycle_fields_aligns_with_legacy_collector() -> None:
    resolver_rows = LifeCycleIntentResolver.resolve_lifecycle_fields(LifecycleEntity)
    legacy_rows = collect_entity_lifecycles(LifecycleEntity)
    assert [(r.field_name, r.lifecycle_class) for r in resolver_rows] == [
        (item.field_name, item.lifecycle_class) for item in legacy_rows
    ]


def test_resolve_finite_state_machine_returns_readonly_states() -> None:
    fsm = LifeCycleIntentResolver.resolve_finite_state_machine(LifecycleEntity, "lifecycle")
    assert fsm.lifecycle_class is DraftLifecycle
    assert isinstance(fsm.states, MappingProxyType)
    keys = set(fsm.states)
    assert keys == {"draft", "active", "archived"}
    assert fsm.states["draft"].state_type is StateType.INITIAL
    assert fsm.states["archived"].state_type is StateType.FINAL
    assert fsm.states["draft"].transitions == frozenset({"active"})


def test_resolve_finite_state_machine_strips_field_name() -> None:
    alt = LifeCycleIntentResolver.resolve_finite_state_machine(LifecycleEntity, "  lifecycle\t")
    assert alt.lifecycle_class is DraftLifecycle


def test_entity_without_lifecycle_fields_returns_empty() -> None:
    assert LifeCycleIntentResolver.resolve_lifecycle_fields(RelatedEntity) == []


def test_unknown_field_raises_value_error() -> None:
    with pytest.raises(ValueError, match="no resolved lifecycle template"):
        LifeCycleIntentResolver.resolve_finite_state_machine(LifecycleEntity, "missing_lc")
