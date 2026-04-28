# tests/intents/connection/test_connection_intent_resolver.py
"""Connection intent resolver behavior."""

from tests.scenarios.domain_model.full_action import FullAction
from tests.scenarios.domain_model.ping_action import PingAction
from tests.scenarios.domain_model.test_db_manager import OrdersDbManager

from action_machine.intents.connection.connection_intent_resolver import (
    ConnectionIntentResolver,
)


def test_resolve_connection_types_returns_declared_resource_types() -> None:
    assert ConnectionIntentResolver.resolve_connection_types(FullAction) == [
        OrdersDbManager,
    ]


def test_resolve_connection_types_returns_empty_list_without_declarations() -> None:
    assert ConnectionIntentResolver.resolve_connection_types(PingAction) == []


def test_resolve_connection_types_and_keys_pairs_type_with_key() -> None:
    assert ConnectionIntentResolver.resolve_connection_types_and_keys(FullAction) == [
        (OrdersDbManager, "db"),
    ]


def test_resolve_connection_types_and_keys_empty_without_declarations() -> None:
    assert ConnectionIntentResolver.resolve_connection_types_and_keys(PingAction) == []
