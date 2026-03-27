# tests/core/test_gate_coordinator_graph.py
"""
Тесты для графа сущностей в GateCoordinator (этап 4).

Полный набор тестов, покрывающий функциональность графа на rustworkx
в GateCoordinator: построение графа, рекурсивный обход зависимостей,
проверку ацикличности, публичный API чтения графа, инвалидацию,
свойства графа.
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
    """Создаёт фейковый async-метод с нужным числом параметров."""
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
    """
    Получает ключ узла класса в графе, используя metadata.class_name
    из координатора.
    """
    metadata = coordinator.get(cls)
    if metadata.has_subscriptions():
        node_type = "plugin"
    elif metadata.has_aspects():
        node_type = "action"
    else:
        node_type = "dependency"
    return f"{node_type}:{metadata.class_name}"


def _attach_aspects(attrs: dict[str, Any], aspects: list[tuple[str, str, str]]) -> None:
    """Добавляет аспекты в словарь атрибутов класса."""
    for method_name, aspect_type, description in aspects:
        method = _make_async_method(method_name)
        method._new_aspect_meta = {
            "type": aspect_type,
            "description": description,
        }
        attrs[method_name] = method


def _attach_checkers(
    attrs: dict[str, Any],
    checkers: list[tuple[str, type, str, str, bool]],
) -> None:
    """Добавляет чекеры к существующим методам-аспектам."""
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
    """Добавляет чувствительные свойства в словарь атрибутов класса."""
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
    """Создаёт тестовый класс с заданными метаданными."""
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
        cls._depends_info = [
            FakeDependencyInfo(cls=dep_cls, description=dep_desc)
            for dep_cls, dep_desc in deps
        ]
    if conns:
        cls._connection_info = [
            FakeConnectionInfo(cls=conn_cls, key=conn_key, description=conn_desc)
            for conn_cls, conn_key, conn_desc in conns
        ]

    return cls


def make_plugin_class(
    name: str = "TestPlugin",
    subscriptions: list[tuple[str, str, str]] | None = None,
) -> type:
    """Создаёт тестовый класс плагина с подписками."""
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
        assert "EmptyClass" in nodes[0]["name"]

    def test_register_action_creates_action_node(self):
        coordinator = GateCoordinator()
        cls = make_action_class(
            name="MyAction",
            aspects=[("step", "regular", "Шаг"), ("finish", "summary", "Итог")],
        )
        coordinator.get(cls)
        actions = coordinator.get_nodes_by_type("action")
        assert len(actions) == 1
        assert "MyAction" in actions[0]["name"]
        assert actions[0]["meta"]["aspect_count"] == 2

    def test_register_plugin_creates_plugin_node(self):
        coordinator = GateCoordinator()
        cls = make_plugin_class(
            name="MyPlugin",
            subscriptions=[("on_finish", "global_finish", ".*")],
        )
        coordinator.get(cls)
        plugins = coordinator.get_nodes_by_type("plugin")
        assert len(plugins) == 1
        assert "MyPlugin" in plugins[0]["name"]
        assert plugins[0]["meta"]["subscription_count"] == 1

    def test_register_action_with_role_creates_role_node(self):
        coordinator = GateCoordinator()
        cls = make_action_class(
            name="AdminAction",
            role_spec="admin",
            aspects=[("summary", "summary", "Итог")],
        )
        coordinator.get(cls)
        roles = coordinator.get_nodes_by_type("role")
        assert len(roles) == 1
        assert roles[0]["meta"]["spec"] == "admin"
        node_key = _get_class_node_key(coordinator, cls)
        children = coordinator.get_children(node_key)
        role_children = [c for c in children if c["node_type"] == "role"]
        assert len(role_children) == 1


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Зависимости и соединения
# ═════════════════════════════════════════════════════════════════════════════


class TestGraphDependenciesAndConnections:

    def test_dependencies_create_nodes_and_edges(self):
        coordinator = GateCoordinator()
        cls = make_action_class(
            name="ActionWithDeps",
            deps=[(FakeServiceA, "Сервис A"), (FakeServiceB, "Сервис B")],
            aspects=[("summary", "summary", "Итог")],
        )
        coordinator.get(cls)
        deps = coordinator.get_nodes_by_type("dependency")
        dep_names = [d["name"] for d in deps]
        assert any("FakeServiceA" in n for n in dep_names)
        assert any("FakeServiceB" in n for n in dep_names)
        node_key = _get_class_node_key(coordinator, cls)
        children = coordinator.get_children(node_key)
        dep_children = [c for c in children if c["node_type"] == "dependency"]
        assert len(dep_children) == 2

    def test_connections_create_nodes_and_edges(self):
        coordinator = GateCoordinator()
        cls = make_action_class(
            name="ActionWithConns",
            conns=[
                (FakeResourceManager, "db", "База данных"),
                (AnotherResourceManager, "cache", "Кеш"),
            ],
            aspects=[("summary", "summary", "Итог")],
        )
        coordinator.get(cls)
        conns = coordinator.get_nodes_by_type("connection")
        conn_names = [c["name"] for c in conns]
        assert any("FakeResourceManager" in n for n in conn_names)
        assert any("AnotherResourceManager" in n for n in conn_names)
        for c in conns:
            assert c["meta"]["key"] in ("db", "cache")

    def test_same_dependency_shared_between_actions(self):
        coordinator = GateCoordinator()
        action1 = make_action_class(
            name="Action1", deps=[(FakeServiceA, "A")],
            aspects=[("summary", "summary", "Итог")],
        )
        action2 = make_action_class(
            name="Action2", deps=[(FakeServiceA, "A тоже")],
            aspects=[("summary", "summary", "Итог")],
        )
        coordinator.get(action1)
        coordinator.get(action2)
        deps = coordinator.get_nodes_by_type("dependency")
        service_a_nodes = [d for d in deps if "FakeServiceA" in d["name"]]
        assert len(service_a_nodes) == 1


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Аспекты и чекеры
# ═════════════════════════════════════════════════════════════════════════════


class TestGraphAspectsAndCheckers:

    def test_aspects_create_nodes_and_edges(self):
        coordinator = GateCoordinator()
        cls = make_action_class(
            name="ActionWithAspects",
            aspects=[
                ("validate", "regular", "Валидация"),
                ("process", "regular", "Обработка"),
                ("finish", "summary", "Результат"),
            ],
        )
        coordinator.get(cls)
        aspects = coordinator.get_nodes_by_type("aspect")
        assert len(aspects) == 3
        assert {a["meta"]["aspect_type"] for a in aspects} == {"regular", "summary"}

    def test_checkers_create_nodes_and_edges(self):
        coordinator = GateCoordinator()
        cls = make_action_class(
            name="ActionWithCheckers",
            aspects=[("process", "regular", "Обработка"), ("finish", "summary", "Результат")],
            checkers=[
                ("process", FakeChecker, "txn_id", "ID транзакции", True),
                ("process", FakeChecker, "amount", "Сумма", False),
            ],
        )
        coordinator.get(cls)
        checkers = coordinator.get_nodes_by_type("checker")
        assert len(checkers) == 2
        assert {c["meta"]["field_name"] for c in checkers} == {"txn_id", "amount"}
        metadata = coordinator.get(cls)
        aspect_key = f"aspect:{metadata.class_name}.process"
        aspect_children = coordinator.get_children(aspect_key)
        checker_children = [c for c in aspect_children if c["node_type"] == "checker"]
        assert len(checker_children) == 2


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Подписки и чувствительные поля
# ═════════════════════════════════════════════════════════════════════════════


class TestGraphSubscriptionsAndSensitive:

    def test_subscriptions_create_nodes_and_edges(self):
        coordinator = GateCoordinator()
        cls = make_plugin_class(
            name="MetricsPlugin",
            subscriptions=[
                ("on_finish", "global_finish", ".*"),
                ("on_before", "aspect_before", "CreateOrder.*"),
            ],
        )
        coordinator.get(cls)
        subs = coordinator.get_nodes_by_type("subscription")
        assert len(subs) == 2
        assert {s["meta"]["event_type"] for s in subs} == {"global_finish", "aspect_before"}

    def test_sensitive_fields_create_nodes_and_edges(self):
        coordinator = GateCoordinator()
        cls = make_action_class(
            name="UserModel", role_spec=None,
            sensitive=[
                ("email", {"enabled": True, "max_chars": 3, "char": "*", "max_percent": 50}),
                ("phone", {"enabled": True, "max_chars": 4, "char": "#", "max_percent": 100}),
            ],
        )
        coordinator.get(cls)
        sf = coordinator.get_nodes_by_type("sensitive")
        assert len(sf) == 2
        assert {s["meta"]["property_name"] for s in sf} == {"email", "phone"}


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Рекурсивный обход зависимостей
# ═════════════════════════════════════════════════════════════════════════════


class TestGraphRecursiveCollection:

    def test_dependency_class_automatically_registered(self):
        coordinator = GateCoordinator()
        cls = make_action_class(
            name="ActionWithDep", deps=[(FakeServiceA, "A")],
            aspects=[("summary", "summary", "Итог")],
        )
        coordinator.get(cls)
        assert coordinator.has(FakeServiceA)

    def test_connection_class_automatically_registered(self):
        coordinator = GateCoordinator()
        cls = make_action_class(
            name="ActionWithConn", conns=[(FakeResourceManager, "db", "БД")],
            aspects=[("summary", "summary", "Итог")],
        )
        coordinator.get(cls)
        assert coordinator.has(FakeResourceManager)

    def test_transitive_dependencies_registered(self):
        coordinator = GateCoordinator()
        service_b_cls = type("ServiceB", (), {})
        service_b_cls._depends_info = [FakeDependencyInfo(cls=FakeServiceC, description="C")]
        action_cls = make_action_class(
            name="ActionA", deps=[(service_b_cls, "B")],
            aspects=[("summary", "summary", "Итог")],
        )
        coordinator.get(action_cls)
        assert coordinator.has(action_cls)
        assert coordinator.has(service_b_cls)
        assert coordinator.has(FakeServiceC)

    def test_duplicate_dependency_not_collected_twice(self):
        coordinator = GateCoordinator()
        action1 = make_action_class(
            name="Action1", deps=[(FakeServiceA, "A")],
            aspects=[("summary", "summary", "Итог")],
        )
        action2 = make_action_class(
            name="Action2", deps=[(FakeServiceA, "A")],
            aspects=[("summary", "summary", "Итог")],
        )
        coordinator.get(action1)
        coordinator.get(action2)
        deps = coordinator.get_nodes_by_type("dependency")
        assert len([d for d in deps if "FakeServiceA" in d["name"]]) == 1


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Проверка ацикличности
# ═════════════════════════════════════════════════════════════════════════════


class TestGraphAcyclicity:

    def test_acyclic_graph_passes(self):
        coordinator = GateCoordinator()
        cls = make_action_class(
            name="AcyclicAction",
            deps=[(FakeServiceA, "A"), (FakeServiceB, "B")],
            aspects=[("summary", "summary", "Итог")],
        )
        coordinator.get(cls)
        assert coordinator.graph_node_count > 0

    def test_self_dependency_detected(self):
        coordinator = GateCoordinator()
        cls = type("SelfDependent", (), {})
        cls._depends_info = [FakeDependencyInfo(cls=cls, description="Сам от себя")]
        with pytest.raises(CyclicDependencyError, match="циклическая зависимость"):
            coordinator.get(cls)

    def test_mutual_dependency_detected(self):
        coordinator = GateCoordinator()
        cls_b = type("ClassB", (), {})
        cls_a = type("ClassA", (), {})
        cls_a._depends_info = [FakeDependencyInfo(cls=cls_b, description="B")]
        cls_b._depends_info = [FakeDependencyInfo(cls=cls_a, description="A")]
        with pytest.raises(CyclicDependencyError, match="циклическая зависимость"):
            coordinator.get(cls_a)

    def test_three_class_cycle_detected(self):
        coordinator = GateCoordinator()
        cls_c = type("ClassC", (), {})
        cls_b = type("ClassB", (), {})
        cls_a = type("ClassA", (), {})
        cls_a._depends_info = [FakeDependencyInfo(cls=cls_b, description="B")]
        cls_b._depends_info = [FakeDependencyInfo(cls=cls_c, description="C")]
        cls_c._depends_info = [FakeDependencyInfo(cls=cls_a, description="A")]
        with pytest.raises(CyclicDependencyError, match="циклическая зависимость"):
            coordinator.get(cls_a)

    def test_diamond_dependency_no_cycle(self):
        coordinator = GateCoordinator()
        cls_d = type("ClassD", (), {})
        cls_b = type("ClassB", (), {})
        cls_b._depends_info = [FakeDependencyInfo(cls=cls_d, description="D")]
        cls_c = type("ClassC", (), {})
        cls_c._depends_info = [FakeDependencyInfo(cls=cls_d, description="D")]
        cls_a = make_action_class(
            name="ClassA", deps=[(cls_b, "B"), (cls_c, "C")],
            aspects=[("summary", "summary", "Итог")],
        )
        coordinator.get(cls_a)
        assert coordinator.has(cls_d)
        assert coordinator.has(cls_b)
        assert coordinator.has(cls_c)


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Публичный API чтения графа
# ═════════════════════════════════════════════════════════════════════════════


class TestGraphPublicAPI:

    def setup_method(self):
        self.coordinator = GateCoordinator()
        self.cls = make_action_class(
            name="FullAction", role_spec="admin",
            deps=[(FakeServiceA, "Сервис A")],
            conns=[(FakeResourceManager, "db", "БД")],
            aspects=[("validate", "regular", "Валидация"), ("finish", "summary", "Результат")],
            checkers=[("validate", FakeChecker, "name", "Имя", True)],
            sensitive=[("email", {"enabled": True, "max_chars": 3, "char": "*", "max_percent": 50})],
        )
        self.coordinator.get(self.cls)
        self.metadata = self.coordinator.get(self.cls)
        self.node_key = _get_class_node_key(self.coordinator, self.cls)

    def test_get_graph_returns_copy(self):
        graph = self.coordinator.get_graph()
        original_count = self.coordinator.graph_node_count
        graph.add_node({"node_type": "test", "name": "extra"})
        assert self.coordinator.graph_node_count == original_count

    def test_get_graph_is_digraph(self):
        assert isinstance(self.coordinator.get_graph(), rx.PyDiGraph)

    def test_get_node_existing(self):
        node = self.coordinator.get_node(self.node_key)
        assert node is not None
        assert node["node_type"] == "action"
        assert "FullAction" in node["name"]
        assert node["class_ref"] is self.cls
        assert node["meta"]["role"] == "admin"
        assert node["meta"]["aspect_count"] == 2

    def test_get_node_missing(self):
        assert self.coordinator.get_node("action:NonExistent") is None

    def test_get_children_of_action(self):
        children = self.coordinator.get_children(self.node_key)
        child_types = {c["node_type"] for c in children}
        assert "aspect" in child_types
        assert "sensitive" in child_types
        assert "role" in child_types
        assert "dependency" in child_types or "connection" in child_types

    def test_get_children_of_missing_node(self):
        assert self.coordinator.get_children("action:NonExistent") == []

    def test_get_nodes_by_type_action(self):
        actions = self.coordinator.get_nodes_by_type("action")
        assert len(actions) >= 1
        assert any("FullAction" in a["name"] for a in actions)

    def test_get_nodes_by_type_empty(self):
        assert self.coordinator.get_nodes_by_type("nonexistent_type") == []

    def test_get_dependency_tree_structure(self):
        tree = self.coordinator.get_dependency_tree(self.node_key)
        assert tree["node_type"] == "action"
        assert "FullAction" in tree["name"]
        assert len(tree["children"]) > 0
        for child in tree["children"]:
            assert "edge_type" in child
            assert child["edge_type"] in (
                "depends", "connection", "has_aspect", "has_sensitive", "has_role",
            )

    def test_get_dependency_tree_missing_node(self):
        assert self.coordinator.get_dependency_tree("action:NonExistent") == {}

    def test_get_dependency_tree_checkers_nested_under_aspects(self):
        tree = self.coordinator.get_dependency_tree(self.node_key)
        aspect_children = [
            c for c in tree["children"]
            if c["node_type"] == "aspect" and "validate" in c["name"]
        ]
        assert len(aspect_children) == 1
        checker_children = [
            c for c in aspect_children[0]["children"] if c["node_type"] == "checker"
        ]
        assert len(checker_children) == 1
        assert checker_children[0]["meta"]["field_name"] == "name"


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Инвалидация и граф
# ═════════════════════════════════════════════════════════════════════════════


class TestGraphInvalidation:

    def test_invalidate_removes_nodes_from_graph(self):
        coordinator = GateCoordinator()
        cls = make_action_class(
            name="TempAction", role_spec="user",
            aspects=[("step", "regular", "Шаг"), ("finish", "summary", "Итог")],
        )
        coordinator.get(cls)
        nodes_before = coordinator.graph_node_count
        assert nodes_before > 0
        coordinator.invalidate(cls)
        assert coordinator.graph_node_count < nodes_before
        actions = coordinator.get_nodes_by_type("action")
        assert not any("TempAction" in a["name"] for a in actions)

    def test_invalidate_all_clears_graph(self):
        coordinator = GateCoordinator()
        cls1 = make_action_class(name="Action1", aspects=[("summary", "summary", "Итог")])
        cls2 = make_action_class(name="Action2", aspects=[("summary", "summary", "Итог")])
        coordinator.get(cls1)
        coordinator.get(cls2)
        assert coordinator.graph_node_count > 0
        coordinator.invalidate_all()
        assert coordinator.graph_node_count == 0
        assert coordinator.graph_edge_count == 0

    def test_invalidate_preserves_shared_dependency_node(self):
        coordinator = GateCoordinator()
        action1 = make_action_class(
            name="Act1", deps=[(FakeServiceA, "A")],
            aspects=[("summary", "summary", "Итог")],
        )
        action2 = make_action_class(
            name="Act2", deps=[(FakeServiceA, "A")],
            aspects=[("summary", "summary", "Итог")],
        )
        coordinator.get(action1)
        coordinator.get(action2)
        coordinator.invalidate(action1)
        assert coordinator.has(FakeServiceA)
        deps = coordinator.get_nodes_by_type("dependency")
        assert len([d for d in deps if "FakeServiceA" in d["name"]]) == 1


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Свойства и repr
# ═════════════════════════════════════════════════════════════════════════════


class TestGraphProperties:

    def test_graph_node_count(self):
        coordinator = GateCoordinator()
        assert coordinator.graph_node_count == 0
        cls = make_action_class(name="CountAction", aspects=[("summary", "summary", "Итог")])
        coordinator.get(cls)
        assert coordinator.graph_node_count > 0

    def test_graph_edge_count(self):
        coordinator = GateCoordinator()
        assert coordinator.graph_edge_count == 0
        cls = make_action_class(
            name="EdgeAction", deps=[(FakeServiceA, "A")],
            aspects=[("summary", "summary", "Итог")],
        )
        coordinator.get(cls)
        assert coordinator.graph_edge_count > 0

    def test_repr_includes_graph_info(self):
        coordinator = GateCoordinator()
        cls = make_action_class(name="ReprAction", aspects=[("summary", "summary", "Итог")])
        coordinator.get(cls)
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
            name="CompleteAction", role_spec="admin",
            deps=[(FakeServiceA, "Платежи"), (FakeServiceB, "Уведомления")],
            conns=[(FakeResourceManager, "db", "БД")],
            aspects=[
                ("validate", "regular", "Валидация"),
                ("process", "regular", "Обработка"),
                ("build_result", "summary", "Результат"),
            ],
            checkers=[
                ("validate", FakeChecker, "amount", "Сумма", True),
                ("process", FakeChecker, "txn_id", "ID транзакции", True),
            ],
            sensitive=[("email", {"enabled": True, "max_chars": 3, "char": "*", "max_percent": 50})],
        )
        coordinator.get(cls)
        all_types = set()
        graph = coordinator.get_graph()
        for idx in graph.node_indices():
            all_types.add(graph[idx]["node_type"])
        for expected in ("action", "dependency", "connection", "aspect", "checker", "sensitive", "role"):
            assert expected in all_types
        node_key = _get_class_node_key(coordinator, cls)
        tree = coordinator.get_dependency_tree(node_key)
        assert tree["node_type"] == "action"
        assert len(tree["children"]) > 0
        assert coordinator.graph_node_count >= 11

    def test_multiple_actions_shared_graph(self):
        coordinator = GateCoordinator()
        action1 = make_action_class(
            name="OrderAction", deps=[(FakeServiceA, "Платежи")],
            aspects=[("summary", "summary", "Итог")],
        )
        action2 = make_action_class(
            name="RefundAction", deps=[(FakeServiceA, "Платежи")],
            aspects=[("summary", "summary", "Итог")],
        )
        coordinator.get(action1)
        coordinator.get(action2)
        assert len(coordinator.get_nodes_by_type("action")) == 2
        deps = coordinator.get_nodes_by_type("dependency")
        assert len([d for d in deps if "FakeServiceA" in d["name"]]) == 1

    def test_plugin_and_action_in_same_graph(self):
        coordinator = GateCoordinator()
        action = make_action_class(name="SomeAction", aspects=[("summary", "summary", "Итог")])
        plugin = make_plugin_class(
            name="SomePlugin", subscriptions=[("on_finish", "global_finish", ".*")],
        )
        coordinator.get(action)
        coordinator.get(plugin)
        assert len(coordinator.get_nodes_by_type("action")) == 1
        assert len(coordinator.get_nodes_by_type("plugin")) == 1
        assert coordinator.graph_node_count >= 4
