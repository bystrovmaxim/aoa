# tests/core/test_gate_coordinator_graph.py
"""
Тесты для графа сущностей в GateCoordinator.

Полный набор тестов, покрывающий функциональность графа на rustworkx:
построение графа, рекурсивный обход зависимостей, проверку ацикличности,
публичный API чтения графа, инвалидацию, свойства графа.

MetadataBuilder импортируется из нового подпакета action_machine.metadata.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest
import rustworkx as rx

from action_machine.core.exceptions import CyclicDependencyError
from action_machine.core.gate_coordinator import GateCoordinator
from action_machine.resource_managers.base_resource_manager import BaseResourceManager

# ═════════════════════════════════════════════════════════════════════════════
# Вспомогательные frozen-датаклассы
# ═════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class FakeDependencyInfo:
    cls: type
    description: str = ""


@dataclass(frozen=True)
class FakeConnectionInfo:
    cls: type
    key: str
    description: str = ""


@dataclass(frozen=True)
class FakeSubscriptionInfo:
    event_type: str
    action_filter: str = ".*"
    ignore_exceptions: bool = True


# ═════════════════════════════════════════════════════════════════════════════
# Вспомогательные классы-сервисы
# ═════════════════════════════════════════════════════════════════════════════


class FakeServiceA:
    pass


class FakeServiceB:
    pass


class FakeServiceC:
    pass


class FakeResourceManager(BaseResourceManager):
    def get_wrapper_class(self):
        return None


class AnotherResourceManager(BaseResourceManager):
    def get_wrapper_class(self):
        return None


class FakeChecker:
    pass


# ═════════════════════════════════════════════════════════════════════════════
# Вспомогательные функции
# ═════════════════════════════════════════════════════════════════════════════


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


def _attach_aspects(attrs: dict[str, Any], aspects: list[tuple[str, str, str]]) -> None:
    for method_name, aspect_type, description in aspects:
        method = _make_async_method(method_name)
        method._new_aspect_meta = {"type": aspect_type, "description": description}
        attrs[method_name] = method


def _attach_checkers(attrs: dict[str, Any], checkers: list[tuple[str, type, str, str, bool]]) -> None:
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


def _attach_sensitive(attrs: dict[str, Any], sensitive: list[tuple[str, dict]]) -> None:
    for prop_name, config in sensitive:
        def make_getter(val):
            def getter(self):
                return val
            return getter
        getter = make_getter(f"value_of_{prop_name}")
        getter._sensitive_config = dict(config)
        attrs[prop_name] = property(getter)


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
        _attach_aspects(attrs, aspects)
    if checkers:
        _attach_checkers(attrs, checkers)
    if sensitive:
        _attach_sensitive(attrs, sensitive)

    cls = type(name, (), attrs)
    if role_spec is not None:
        cls._role_info = {"spec": role_spec, "desc": ""}
    if deps:
        cls._depends_info = [FakeDependencyInfo(cls=d, description=desc) for d, desc in deps]
    if conns:
        cls._connection_info = [FakeConnectionInfo(cls=c, key=k, description=d) for c, k, d in conns]
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
                FakeSubscriptionInfo(event_type=event_type, action_filter=action_filter)
            ]
            attrs[method_name] = method
    return type(name, (), attrs)


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Построение графа — базовые узлы
# ═════════════════════════════════════════════════════════════════════════════


class TestGraphBasicNodes:

    def test_empty_coordinator_has_empty_graph(self):
        coordinator = GateCoordinator()
        assert coordinator.graph_node_count == 0
        assert coordinator.graph_edge_count == 0

    def test_register_empty_class_creates_dependency_node(self):
        coordinator = GateCoordinator()
        cls = type("EmptyClass", (), {})
        coordinator.get(cls)
        assert coordinator.graph_node_count == 1
        nodes = coordinator.get_nodes_by_type("dependency")
        assert len(nodes) == 1

    def test_register_action_creates_action_node(self):
        coordinator = GateCoordinator()
        cls = make_action_class(
            name="MyAction",
            aspects=[("step", "regular", "Шаг"), ("finish", "summary", "Итог")],
        )
        coordinator.get(cls)
        actions = coordinator.get_nodes_by_type("action")
        assert len(actions) == 1
        assert actions[0]["meta"]["aspect_count"] == 2

    def test_register_plugin_creates_plugin_node(self):
        coordinator = GateCoordinator()
        cls = make_plugin_class(name="MyPlugin", subscriptions=[("on_finish", "global_finish", ".*")])
        coordinator.get(cls)
        plugins = coordinator.get_nodes_by_type("plugin")
        assert len(plugins) == 1

    def test_register_action_with_role_creates_role_node(self):
        coordinator = GateCoordinator()
        cls = make_action_class(name="AdminAction", role_spec="admin",
                                aspects=[("summary", "summary", "Итог")])
        coordinator.get(cls)
        roles = coordinator.get_nodes_by_type("role")
        assert len(roles) == 1
        assert roles[0]["meta"]["spec"] == "admin"


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Зависимости и соединения
# ═════════════════════════════════════════════════════════════════════════════


class TestGraphDependenciesAndConnections:

    def test_dependencies_create_nodes_and_edges(self):
        coordinator = GateCoordinator()
        cls = make_action_class(
            name="ActionWithDeps",
            deps=[(FakeServiceA, "A"), (FakeServiceB, "B")],
            aspects=[("summary", "summary", "Итог")],
        )
        coordinator.get(cls)
        deps = coordinator.get_nodes_by_type("dependency")
        dep_names = [d["name"] for d in deps]
        assert any("FakeServiceA" in n for n in dep_names)
        assert any("FakeServiceB" in n for n in dep_names)

    def test_connections_create_nodes_and_edges(self):
        coordinator = GateCoordinator()
        cls = make_action_class(
            name="ActionWithConns",
            conns=[(FakeResourceManager, "db", "БД"), (AnotherResourceManager, "cache", "Кеш")],
            aspects=[("summary", "summary", "Итог")],
        )
        coordinator.get(cls)
        conns = coordinator.get_nodes_by_type("connection")
        assert len(conns) == 2

    def test_same_dependency_shared_between_actions(self):
        coordinator = GateCoordinator()
        a1 = make_action_class(name="A1", deps=[(FakeServiceA, "A")],
                                aspects=[("summary", "summary", "")])
        a2 = make_action_class(name="A2", deps=[(FakeServiceA, "A")],
                                aspects=[("summary", "summary", "")])
        coordinator.get(a1)
        coordinator.get(a2)
        deps = coordinator.get_nodes_by_type("dependency")
        assert len([d for d in deps if "FakeServiceA" in d["name"]]) == 1


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Аспекты и чекеры
# ═════════════════════════════════════════════════════════════════════════════


class TestGraphAspectsAndCheckers:

    def test_aspects_create_nodes_and_edges(self):
        coordinator = GateCoordinator()
        cls = make_action_class(
            name="WithAspects",
            aspects=[("validate", "regular", ""), ("process", "regular", ""), ("finish", "summary", "")],
        )
        coordinator.get(cls)
        assert len(coordinator.get_nodes_by_type("aspect")) == 3

    def test_checkers_create_nodes_and_edges(self):
        coordinator = GateCoordinator()
        cls = make_action_class(
            name="WithCheckers",
            aspects=[("process", "regular", ""), ("finish", "summary", "")],
            checkers=[("process", FakeChecker, "txn_id", "", True),
                      ("process", FakeChecker, "amount", "", False)],
        )
        coordinator.get(cls)
        assert len(coordinator.get_nodes_by_type("checker")) == 2


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Подписки и чувствительные поля
# ═════════════════════════════════════════════════════════════════════════════


class TestGraphSubscriptionsAndSensitive:

    def test_subscriptions_create_nodes(self):
        coordinator = GateCoordinator()
        cls = make_plugin_class(name="MP", subscriptions=[
            ("on_finish", "global_finish", ".*"),
            ("on_before", "aspect_before", "Create.*"),
        ])
        coordinator.get(cls)
        assert len(coordinator.get_nodes_by_type("subscription")) == 2

    def test_sensitive_fields_create_nodes(self):
        coordinator = GateCoordinator()
        cls = make_action_class(
            name="UserModel", role_spec=None,
            sensitive=[
                ("email", {"enabled": True, "max_chars": 3, "char": "*", "max_percent": 50}),
                ("phone", {"enabled": True, "max_chars": 4, "char": "#", "max_percent": 100}),
            ],
        )
        coordinator.get(cls)
        assert len(coordinator.get_nodes_by_type("sensitive")) == 2


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Рекурсивный обход зависимостей
# ═════════════════════════════════════════════════════════════════════════════


class TestGraphRecursiveCollection:

    def test_dependency_class_automatically_registered(self):
        coordinator = GateCoordinator()
        cls = make_action_class(name="A", deps=[(FakeServiceA, "A")],
                                aspects=[("summary", "summary", "")])
        coordinator.get(cls)
        assert coordinator.has(FakeServiceA)

    def test_transitive_dependencies_registered(self):
        coordinator = GateCoordinator()
        svc_b = type("ServiceB", (), {})
        svc_b._depends_info = [FakeDependencyInfo(cls=FakeServiceC)]
        action = make_action_class(name="ActionA", deps=[(svc_b, "B")],
                                    aspects=[("summary", "summary", "")])
        coordinator.get(action)
        assert coordinator.has(FakeServiceC)


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Проверка ацикличности
# ═════════════════════════════════════════════════════════════════════════════


class TestGraphAcyclicity:

    def test_self_dependency_detected(self):
        coordinator = GateCoordinator()
        cls = type("SelfDep", (), {})
        cls._depends_info = [FakeDependencyInfo(cls=cls)]
        with pytest.raises(CyclicDependencyError, match="циклическая зависимость"):
            coordinator.get(cls)

    def test_mutual_dependency_detected(self):
        coordinator = GateCoordinator()
        cls_b = type("B", (), {})
        cls_a = type("A", (), {})
        cls_a._depends_info = [FakeDependencyInfo(cls=cls_b)]
        cls_b._depends_info = [FakeDependencyInfo(cls=cls_a)]
        with pytest.raises(CyclicDependencyError, match="циклическая зависимость"):
            coordinator.get(cls_a)

    def test_diamond_dependency_no_cycle(self):
        coordinator = GateCoordinator()
        cls_d = type("D", (), {})
        cls_b = type("B", (), {})
        cls_b._depends_info = [FakeDependencyInfo(cls=cls_d)]
        cls_c = type("C", (), {})
        cls_c._depends_info = [FakeDependencyInfo(cls=cls_d)]
        cls_a = make_action_class(name="A", deps=[(cls_b, "B"), (cls_c, "C")],
                                   aspects=[("summary", "summary", "")])
        coordinator.get(cls_a)
        assert coordinator.has(cls_d)


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Публичный API чтения графа
# ═════════════════════════════════════════════════════════════════════════════


class TestGraphPublicAPI:

    def setup_method(self):
        self.coordinator = GateCoordinator()
        self.cls = make_action_class(
            name="FullAction", role_spec="admin",
            deps=[(FakeServiceA, "A")],
            conns=[(FakeResourceManager, "db", "БД")],
            aspects=[("validate", "regular", ""), ("finish", "summary", "")],
            checkers=[("validate", FakeChecker, "name", "", True)],
            sensitive=[("email", {"enabled": True, "max_chars": 3, "char": "*", "max_percent": 50})],
        )
        self.coordinator.get(self.cls)
        self.node_key = _get_class_node_key(self.coordinator, self.cls)

    def test_get_graph_returns_copy(self):
        graph = self.coordinator.get_graph()
        original = self.coordinator.graph_node_count
        graph.add_node({"node_type": "test", "name": "extra"})
        assert self.coordinator.graph_node_count == original

    def test_get_graph_is_digraph(self):
        assert isinstance(self.coordinator.get_graph(), rx.PyDiGraph)

    def test_get_node_existing(self):
        node = self.coordinator.get_node(self.node_key)
        assert node is not None
        assert node["node_type"] == "action"

    def test_get_node_missing(self):
        assert self.coordinator.get_node("action:NonExistent") is None

    def test_get_children(self):
        children = self.coordinator.get_children(self.node_key)
        child_types = {c["node_type"] for c in children}
        assert "aspect" in child_types

    def test_get_dependency_tree(self):
        tree = self.coordinator.get_dependency_tree(self.node_key)
        assert tree["node_type"] == "action"
        assert len(tree["children"]) > 0

    def test_get_dependency_tree_missing(self):
        assert self.coordinator.get_dependency_tree("action:NonExistent") == {}


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Инвалидация и граф
# ═════════════════════════════════════════════════════════════════════════════


class TestGraphInvalidation:

    def test_invalidate_removes_nodes(self):
        coordinator = GateCoordinator()
        cls = make_action_class(name="Temp", aspects=[("s", "regular", ""), ("f", "summary", "")])
        coordinator.get(cls)
        before = coordinator.graph_node_count
        coordinator.invalidate(cls)
        assert coordinator.graph_node_count < before

    def test_invalidate_all_clears_graph(self):
        coordinator = GateCoordinator()
        coordinator.get(make_action_class(name="A1", aspects=[("s", "summary", "")]))
        coordinator.get(make_action_class(name="A2", aspects=[("s", "summary", "")]))
        coordinator.invalidate_all()
        assert coordinator.graph_node_count == 0


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Свойства и repr
# ═════════════════════════════════════════════════════════════════════════════


class TestGraphProperties:

    def test_graph_node_count(self):
        coordinator = GateCoordinator()
        assert coordinator.graph_node_count == 0
        coordinator.get(make_action_class(name="A", aspects=[("s", "summary", "")]))
        assert coordinator.graph_node_count > 0

    def test_repr_includes_graph_info(self):
        coordinator = GateCoordinator()
        coordinator.get(make_action_class(name="A", aspects=[("s", "summary", "")]))
        r = repr(coordinator)
        assert "nodes=" in r
        assert "edges=" in r

    def test_repr_empty(self):
        assert "empty" in repr(GateCoordinator())


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Интеграция
# ═════════════════════════════════════════════════════════════════════════════


class TestGraphIntegration:

    def test_full_action_graph(self):
        coordinator = GateCoordinator()
        cls = make_action_class(
            name="Complete", role_spec="admin",
            deps=[(FakeServiceA, "A"), (FakeServiceB, "B")],
            conns=[(FakeResourceManager, "db", "БД")],
            aspects=[("validate", "regular", ""), ("process", "regular", ""), ("result", "summary", "")],
            checkers=[("validate", FakeChecker, "amount", "", True)],
            sensitive=[("email", {"enabled": True, "max_chars": 3, "char": "*", "max_percent": 50})],
        )
        coordinator.get(cls)
        all_types = set()
        graph = coordinator.get_graph()
        for idx in graph.node_indices():
            all_types.add(graph[idx]["node_type"])
        for expected in ("action", "dependency", "connection", "aspect", "checker", "sensitive", "role"):
            assert expected in all_types

    def test_plugin_and_action_in_same_graph(self):
        coordinator = GateCoordinator()
        coordinator.get(make_action_class(name="Act", aspects=[("s", "summary", "")]))
        coordinator.get(make_plugin_class(name="Plug", subscriptions=[("h", "global_finish", ".*")]))
        assert len(coordinator.get_nodes_by_type("action")) == 1
        assert len(coordinator.get_nodes_by_type("plugin")) == 1
