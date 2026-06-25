# tests/intents/depends/test_depends_intent_resolver.py
"""Depends intent resolver behavior."""

from aoa.action_machine.intents.depends import UseCase, depends
from aoa.action_machine.intents.depends.depends_intent import DependsIntent
from aoa.action_machine.intents.depends.depends_intent_resolver import DependsIntentResolver

from ....support.domain_model.full_action import FullAction
from ....support.domain_model.ping_action import PingAction
from ....support.domain_model.services import NotificationServiceResource, PaymentServiceResource
from ....support.domain_model.test_db_manager import OrdersDbManager


def test_resolve_dependency_types_returns_declared_dependency_types() -> None:
    assert DependsIntentResolver.resolve_dependency_types(FullAction) == [
        OrdersDbManager,
        NotificationServiceResource,
        PaymentServiceResource,
    ]


def test_resolve_dependency_types_returns_empty_list_without_declarations() -> None:
    assert DependsIntentResolver.resolve_dependency_types(PingAction) == []


def test_resolve_include_dependency_types_filters_include_only() -> None:
    @depends(PingAction, mode=UseCase.include, description="inc")
    @depends(PaymentServiceResource, description="res")
    class _Host(DependsIntent[PingAction | PaymentServiceResource]):
        pass

    assert DependsIntentResolver.resolve_include_dependency_types(_Host) == [PingAction]
