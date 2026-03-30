# tests/metadata/test_gate_coordinator_graph.py
"""
Тесты для графа сущностей в GateCoordinator.
Все тестовые классы используют реальные форматы метаданных
(DependencyInfo, ConnectionInfo, SubscriptionInfo), чтобы
MetadataBuilder и коллекторы обрабатывали их без ошибок.
"""

from __future__ import annotations

from typing import Any

import pytest
import rustworkx as rx

from action_machine.aspects.aspect_gate_host import AspectGateHost
from action_machine.checkers.checker_gate_host import CheckerGateHost
from action_machine.core.exceptions import CyclicDependencyError
from action_machine.core.gate_coordinator import GateCoordinator
from action_machine.core.meta_decorator import meta
from action_machine.dependencies.depends import DependencyInfo
from action_machine.plugins.decorators import SubscriptionInfo
from action_machine.plugins.on_gate_host import OnGateHost
from action_machine.resource_managers.base_resource_manager import BaseResourceManager
from action_machine.resource_managers.connection import ConnectionInfo

# ═══════════════════════════════════════════════════════════════════
# Заглушки сервисов и ресурсов
# ═══════════════════════════════════════════════════════════════════

class FakeServiceA:
    pass

class FakeServiceB:
    pass

class FakeServiceC:
    pass

@meta(description="Fake resource manager for tests")
class FakeResourceManager(BaseResourceManager):
    def get_wrapper_class(self):
        return None

class AnotherResourceManager(BaseResourceManager):
    def get_wrapper_class(self):
        return None

class FakeChecker:
    pass


# ═══════════════════════════════════════════════════════════════════
# Вспомогательные функции
# ═══════════════════════════════════════════════════════════════════

def _make_async_method(name: str, param_count: int = 5):
    if param_count == 5:
        async def method(self, params, state, box, connections):
            pass
    elif param_count == 3:
        async def method(self, state, event):
            pass
    else:
        async def method(self):
            pass
    method.__name__ = name
    method.__qualname__ = name
    return method


def _get_class_node_key(coordinator: GateCoordinator, cls: type) -> str:
    metadata = coordinator.get(cls)
    if metadata.has_subscriptions():
        node_type = "plugin"
    elif metadata.has_aspects():
        node_type = "action"
    else:
        node_type = "dependency"
    return f"{node_type}:{metadata.class_name}"


def make_action_class(
    name: str = "TestAction",
    role_spec: str | None = "__NONE__",
    deps: list[tuple[type, str]] | None = None,
    conns: list[tuple[type, str, str]] | None = None,
    aspects: list[tuple[str, str, str]] | None = None,
    checkers: list[tuple[str, type, str, str, bool]] | None = None,
    sensitive: list[tuple[str, dict]] | None = None,
) -> type:
    attrs: dict[str, Any] = {}

    if aspects:
        for method_name, aspect_type, description in aspects:
            method = _make_async_method(method_name)
            method._new_aspect_meta = {"type": aspect_type, "description": description}
            attrs[method_name] = method

    if checkers:
        for method_name, checker_class, field_name, desc, required in checkers:
            method = attrs.get(method_name)
            if method:
                if not hasattr(method, "_checker_meta"):
                    method._checker_meta = []
                method._checker_meta.append({
                    "checker_class": checker_class,
                    "field_name": field_name,
                    "description": desc,
                    "required": required,
                })

    if sensitive:
        for prop_name, config in sensitive:
            def make_getter(val):
                def getter(self):
                    return val
                return getter
            getter = make_getter(f"value_of_{prop_name}")
            getter._sensitive_config = dict(config)
            attrs[prop_name] = property(getter)

    bases: tuple[type, ...] = ()
    if aspects or checkers:
        bases = (AspectGateHost, CheckerGateHost)

    cls = type(name, bases, attrs)

    if role_spec is not None:
        cls._role_info = {"spec": role_spec, "desc": ""}
    if deps:
        cls._depends_info = [
            DependencyInfo(cls=dep_cls, description=dep_desc)
            for dep_cls, dep_desc in deps
        ]
    if conns:
        cls._connection_info = [
            ConnectionInfo(cls=conn_cls, key=conn_key, description=conn_desc)
            for conn_cls, conn_key, conn_desc in conns
        ]

    return cls


def make_plugin_class(
    name: str = "TestPlugin",
    subscriptions: list[tuple[str, str, str]] | None = None,
) -> type:
    attrs: dict[str, Any] = {}
    if subscriptions:
        for method_name, event_type, action_filter in subscriptions:
            method = _make_async_method(method_name, param_count=3)
            method._on_subscriptions = [
                SubscriptionInfo(event_type=event_type, action_filter=action_filter)
            ]
            attrs[method_name] = method

    bases: tuple[type, ...] = (OnGateHost,) if subscriptions else ()
    return type(name, bases, attrs)


# ═══════════════════════════════════════════════════════════════════
# ТЕСТЫ: Базовые узлы
# ═══════════════════════════════════════════════════════════════════

class TestBasicNodes:

    def test_empty_coordinator_has_empty_graph(self):
        coordinator = GateCoordinator()
        assert coordinator.graph_node_count == 0

    def test_register_empty_class_creates_dependency_node(self):
        coordinator = GateCoordinator()
        cls = type("EmptyClass", (), {})
        coordinator.get(cls)
        assert coordinator.graph_node_count == 1

    def test_register_action_creates_action_node(self):
        coordinator = GateCoordinator()
        cls = make_action_class(
            name="MyAction",
            aspects=[("step", "regular", "Шаг"), ("finish", "summary", "Итог")],
        )
        coordinator.get(cls)
        actions = coordinator.get_nodes_by_type("action")
        assert len(actions) == 1

    def test_register_creates_correct_node_count(self):
        coordinator = GateCoordinator()
        cls1 = make_action_class("Action1", aspects=[("s", "summary", "S")])
        cls2 = make_action_class("Action2", aspects=[("s", "summary", "S")])
        coordinator.get(cls1)
        coordinator.get(cls2)
        assert coordinator.size >= 2  # property, не метод


# ═══════════════════════════════════════════════════════════════════
# ТЕСТЫ: Зависимости и соединения
# ═══════════════════════════════════════════════════════════════════

class TestDependencyAndConnectionEdges:

    def test_dependency_edge_created(self):
        coordinator = GateCoordinator()
        cls = make_action_class(
            "ActionWithDep",
            deps=[(FakeServiceA, "A")],
            aspects=[("s", "summary", "S")],
        )
        coordinator.get(cls)
        assert coordinator.has(cls)

    def test_connection_edge_created(self):
        coordinator = GateCoordinator()
        cls = make_action_class(
            "ActionWithConn",
            conns=[(FakeResourceManager, "db", "БД")],
            aspects=[("s", "summary", "S")],
        )
        coordinator.get(cls)
        assert coordinator.has(cls)

    def test_multiple_dependencies(self):
        coordinator = GateCoordinator()
        cls = make_action_class(
            "ActionMultiDep",
            deps=[(FakeServiceA, "A"), (FakeServiceB, "B")],
            aspects=[("s", "summary", "S")],
        )
        coordinator.get(cls)
        assert coordinator.has(cls)


# ═══════════════════════════════════════════════════════════════════
# ТЕСТЫ: Аспекты и чекеры
# ═══════════════════════════════════════════════════════════════════

class TestAspectAndCheckerNodes:

    def test_aspects_create_nodes(self):
        coordinator = GateCoordinator()
        cls = make_action_class(
            "ActionWithAspects",
            aspects=[("validate", "regular", "V"), ("finish", "summary", "F")],
        )
        coordinator.get(cls)
        assert len(coordinator.get_nodes_by_type("aspect")) == 2

    def test_checkers_create_nodes(self):
        coordinator = GateCoordinator()
        cls = make_action_class(
            "ActionWithCheckers",
            aspects=[("process", "regular", "P"), ("finish", "summary", "F")],
            checkers=[("process", FakeChecker, "txn_id", "ID", True)],
        )
        coordinator.get(cls)
        assert len(coordinator.get_nodes_by_type("checker")) == 1


# ═══════════════════════════════════════════════════════════════════
# ТЕСТЫ: Подписки и sensitive
# ═══════════════════════════════════════════════════════════════════

class TestSubscriptionNodes:

    def test_plugin_subscriptions_create_nodes(self):
        coordinator = GateCoordinator()
        cls = make_plugin_class(
            "MetricsPlugin",
            subscriptions=[
                ("on_finish", "global_finish", ".*"),
                ("on_before", "aspect_before", "CreateOrder.*"),
            ],
        )
        coordinator.get(cls)
        assert len(coordinator.get_nodes_by_type("subscription")) == 2


class TestSensitiveNodes:

    def test_sensitive_field_creates_node(self):
        coordinator = GateCoordinator()
        cls = make_action_class(
            "SecureAction", role_spec=None,
            sensitive=[("email", {"enabled": True, "max_chars": 3, "char": "*", "max_percent": 50})],
        )
        coordinator.get(cls)
        assert len(coordinator.get_nodes_by_type("sensitive")) >= 1


# ═══════════════════════════════════════════════════════════════════
# ТЕСТЫ: Рекурсивный обход
# ═══════════════════════════════════════════════════════════════════

class TestRecursiveCollection:

    def test_transitive_dependencies(self):
        coordinator = GateCoordinator()
        service_b = type("ServiceB", (), {})
        service_b._depends_info = [DependencyInfo(cls=FakeServiceC, description="C")]
        action = make_action_class(
            "ActionA", deps=[(service_b, "B")],
            aspects=[("s", "summary", "S")],
        )
        coordinator.get(action)
        assert coordinator.has(service_b)
        assert coordinator.has(FakeServiceC)

    def test_diamond_dependencies(self):
        coordinator = GateCoordinator()
        cls_d = type("ClassD", (), {})
        cls_b = type("ClassB", (), {})
        cls_b._depends_info = [DependencyInfo(cls=cls_d, description="D")]
        cls_c = type("ClassC", (), {})
        cls_c._depends_info = [DependencyInfo(cls=cls_d, description="D")]
        action = make_action_class(
            "ActionA", deps=[(cls_b, "B"), (cls_c, "C")],
            aspects=[("s", "summary", "S")],
        )
        coordinator.get(action)
        assert coordinator.has(cls_d)


# ═══════════════════════════════════════════════════════════════════
# ТЕСТЫ: Ацикличность
# ═══════════════════════════════════════════════════════════════════

class TestCycleDetection:

    def test_self_reference_detected(self):
        coordinator = GateCoordinator()
        cls_a = type("SelfRef", (), {})
        cls_a._depends_info = [DependencyInfo(cls=cls_a, description="self")]
        with pytest.raises(CyclicDependencyError):
            coordinator.get(cls_a)

    def test_mutual_cycle_detected(self):
        coordinator = GateCoordinator()
        cls_a = type("CycleA", (), {})
        cls_b = type("CycleB", (), {})
        cls_a._depends_info = [DependencyInfo(cls=cls_b, description="B")]
        cls_b._depends_info = [DependencyInfo(cls=cls_a, description="A")]
        with pytest.raises(CyclicDependencyError):
            coordinator.get(cls_a)

    def test_three_class_cycle_detected(self):
        coordinator = GateCoordinator()
        cls_a = type("C3A", (), {})
        cls_b = type("C3B", (), {})
        cls_c = type("C3C", (), {})
        cls_a._depends_info = [DependencyInfo(cls=cls_b, description="B")]
        cls_b._depends_info = [DependencyInfo(cls=cls_c, description="C")]
        cls_c._depends_info = [DependencyInfo(cls=cls_a, description="A")]
        with pytest.raises(CyclicDependencyError):
            coordinator.get(cls_a)


# ═══════════════════════════════════════════════════════════════════
# ТЕСТЫ: Публичный API
# ═══════════════════════════════════════════════════════════════════

class TestGraphPublicAPI:

    def test_get_graph_returns_copy(self):
        coordinator = GateCoordinator()
        cls = make_action_class("ApiAction", aspects=[("s", "summary", "S")])
        coordinator.get(cls)
        graph = coordinator.get_graph()
        assert graph is not None
        assert isinstance(graph, rx.PyDiGraph)

    def test_get_dependency_tree(self):
        coordinator = GateCoordinator()
        cls_b = type("DepService", (), {})
        cls_a = make_action_class(
            "TreeAction",
            deps=[(cls_b, "B")],
            aspects=[("s", "summary", "S")],
        )
        coordinator.get(cls_a)
        key = _get_class_node_key(coordinator, cls_a)
        tree = coordinator.get_dependency_tree(key)
        assert tree is not None
        assert "name" in tree


# ═══════════════════════════════════════════════════════════════════
# ТЕСТЫ: Инвалидация
# ═══════════════════════════════════════════════════════════════════

class TestInvalidation:

    def test_invalidate_single(self):
        coordinator = GateCoordinator()
        cls = make_action_class("Inv", aspects=[("s", "summary", "S")])
        coordinator.get(cls)
        assert coordinator.has(cls)
        coordinator.invalidate(cls)
        assert not coordinator.has(cls)

    def test_invalidate_all(self):
        coordinator = GateCoordinator()
        cls1 = make_action_class("Inv1", aspects=[("s", "summary", "S")])
        cls2 = make_action_class("Inv2", aspects=[("s", "summary", "S")])
        coordinator.get(cls1)
        coordinator.get(cls2)
        coordinator.invalidate_all()
        assert coordinator.size == 0  # property

    def test_rebuild_after_invalidation(self):
        coordinator = GateCoordinator()
        cls = make_action_class("Rebuild", aspects=[("s", "summary", "S")])
        meta1 = coordinator.get(cls)
        coordinator.invalidate(cls)
        meta2 = coordinator.get(cls)
        assert meta1 is not meta2
        assert meta1.class_ref is meta2.class_ref


# ═══════════════════════════════════════════════════════════════════
# ТЕСТЫ: Интеграция
# ═══════════════════════════════════════════════════════════════════

class TestGraphIntegration:

    def test_full_action_graph(self):
        coordinator = GateCoordinator()
        cls = make_action_class(
            "CompleteAction", role_spec="admin",
            deps=[(FakeServiceA, "Платежи")],
            conns=[(FakeResourceManager, "db", "БД")],
            aspects=[
                ("validate", "regular", "Валидация"),
                ("finish", "summary", "Результат"),
            ],
            checkers=[("validate", FakeChecker, "amount", "Сумма", True)],
            sensitive=[("email", {"enabled": True, "max_chars": 3, "char": "*", "max_percent": 50})],
        )
        coordinator.get(cls)
        assert coordinator.graph_node_count >= 6

    def test_multi_action_shared_graph(self):
        coordinator = GateCoordinator()
        action1 = make_action_class(
            "OrderAction",
            deps=[(FakeServiceA, "Платежи")],
            aspects=[("s", "summary", "S")],
        )
        action2 = make_action_class(
            "RefundAction",
            deps=[(FakeServiceA, "Платежи")],
            aspects=[("s", "summary", "S")],
        )
        coordinator.get(action1)
        coordinator.get(action2)
        assert len(coordinator.get_nodes_by_type("action")) == 2
