# tests/intents/depends/test_depends_intent_resolver.py
"""Depends intent resolver behavior."""

from tests.scenarios.domain_model.full_action import FullAction
from tests.scenarios.domain_model.ping_action import PingAction
from tests.scenarios.domain_model.services import (
    NotificationServiceResource,
    PaymentServiceResource,
)
from tests.scenarios.domain_model.test_db_manager import OrdersDbManager

from action_machine.intents.depends.depends_intent_resolver import DependsIntentResolver


def test_resolve_dependency_types_returns_declared_dependency_types() -> None:
    assert DependsIntentResolver.resolve_dependency_types(FullAction) == [
        OrdersDbManager,
        NotificationServiceResource,
        PaymentServiceResource,
    ]


def test_resolve_dependency_types_returns_empty_list_without_declarations() -> None:
    assert DependsIntentResolver.resolve_dependency_types(PingAction) == []
