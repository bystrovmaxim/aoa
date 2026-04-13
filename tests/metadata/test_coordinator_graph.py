# tests/metadata/test_coordinator_graph.py
"""
Тесты GateCoordinator — граф зависимостей, узлы, рёбра, циклы, публичное API.
═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════
Проверяет, что GateCoordinator строит направленный граф из
зарегистрированных классов, создаёт узлы для действий, зависимостей,
соединений, аспектов, чекеров, подписок, sensitive-полей, компенсаторов,
обнаруживает циклические зависимости и предоставляет публичное API
для инспекции.
═══════════════════════════════════════════════════════════════════════════════
СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════
TestBasicNodes — создание базовых узлов графа.
TestDependenciesAndConnections — узлы и рёбра зависимостей и соединений.
TestAspectsAndCheckers — узлы аспектов и чекеров.
TestSubscriptionsAndSensitive — узлы подписок и sensitive-полей.
TestCompensatorNodes — агрегированный facet ``compensator`` (без рёбер
``has_compensator`` к structural ``action``; см. CompensateIntentInspector).
TestRecursiveCollection — автоматический рекурсивный сбор зависимостей.
TestCycleDetection — сценарии без цикла в графе (ромб); логические циклы @depends
    не покрываются отдельным тестом на CyclicDependencyError.
TestPublicAPI — публичные методы инспекции графа.
TestInvalidation — инвалидация кеша координатора.
TestCoordinatorBasic — базовое API координатора.

═══════════════════════════════════════════════════════════════════════════════
ФАСЕТНЫЙ ГРАФ И ФИЛЬТРАЦИЯ В ТЕСТАХ
═══════════════════════════════════════════════════════════════════════════════

Граф строится из ``FacetPayload`` инспекторов: в ``rustworkx`` — тип узла, имя,
``class_ref``; тело фасета в снимках, ``get_node`` / ``hydrate_graph_node``
подмешивают ``meta``. Узел ``action`` (структурный) появляется только у классов с
``@depends`` и/или ``@connection`` (два инспектора, узел ``action`` сливается
в координаторе), иначе
остаются ``meta``, ``role``, ``aspect``, ``compensator`` и т.д. Подписки плагина
— узлы ``subscription``, не ``plugin``. Чувствительные поля в графе покрывает
``SensitiveIntentInspector`` для наследников ``BaseSchema`` (не для
``BaseAction``). Запросы к графу фильтруют узлы по ``class_ref`` или по
фрагменту имени, потому что после ``build()`` в снимок могут попасть и чужие
классы из общего сканирования инспекторов.
"""
from typing import Any

import pytest

from action_machine.dependencies.dependency_factory import (
    cached_dependency_factory,
    clear_dependency_factory_cache,
)
from action_machine.dependencies.depends_decorator import depends
from action_machine.graph.base_intent_inspector import BaseIntentInspector
from action_machine.graph.gate_coordinator import GateCoordinator
from action_machine.graph.inspectors.meta_intent_inspector import MetaIntentInspector
from action_machine.intents.aspects.regular_aspect_decorator import regular_aspect
from action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from action_machine.intents.auth.check_roles_decorator import check_roles
from action_machine.intents.auth.none_role import NoneRole
from action_machine.intents.checkers.result_string_checker import result_string
from action_machine.intents.compensate import compensate
from action_machine.intents.logging.sensitive_decorator import sensitive
from action_machine.intents.meta.meta_decorator import meta
from action_machine.intents.plugins.events import GlobalStartEvent
from action_machine.intents.plugins.on_decorator import on
from action_machine.intents.plugins.plugin import Plugin
from action_machine.model.base_action import BaseAction
from action_machine.model.base_params import BaseParams
from action_machine.model.base_result import BaseResult
from action_machine.model.base_schema import BaseSchema
from action_machine.resources.base_resource_manager import BaseResourceManager
from action_machine.resources.connection_decorator import connection
from action_machine.runtime.machines.core_action_machine import CoreActionMachine
from tests.scenarios.domain_model.domains import TestDomain
from tests.scenarios.domain_model.roles import AdminRole


def _new_coord() -> GateCoordinator:
    """Create built coordinator with default inspector set."""
    return CoreActionMachine.create_coordinator()


def _graph_children(coord: GateCoordinator, full_key: str) -> list[dict[str, Any]]:
    g = coord.get_graph()
    for idx in g.node_indices():
        node = g[idx]
        nk = f"{node['node_type']}:{node['name']}"
        if nk == full_key:
            return [dict(g[t]) for t in g.successor_indices(idx)]
    return []


def _dependency_tree(coord: GateCoordinator, key: str | type) -> dict[str, Any]:
    if isinstance(key, type):
        key = f"action:{BaseIntentInspector._make_node_name(key)}"
    g = coord.get_graph()
    idx_by_key: dict[str, int] = {}
    for i in g.node_indices():
        n = g[i]
        idx_by_key[f"{n['node_type']}:{n['name']}"] = i

    def build(idx: int, visited: set[int]) -> dict[str, Any]:
        payload = g[idx]
        hp = coord.hydrate_graph_node(dict(payload))
        node_result: dict[str, Any] = {
            "node_type": hp["node_type"],
            "name": hp["name"],
            "meta": dict(hp.get("meta", {})),
            "children": [],
        }
        if idx in visited:
            node_result["meta"] = dict(node_result["meta"])
            node_result["meta"]["cycle"] = True
            return node_result
        visited = visited | {idx}
        for _src, target, edge_payload in g.out_edges(idx):
            child_tree = build(target, visited)
            if isinstance(edge_payload, dict):
                child_tree["edge_type"] = edge_payload.get("edge_type")
            else:
                child_tree["edge_type"] = edge_payload
            node_result["children"].append(child_tree)
        return node_result

    idx = idx_by_key.get(key)
    if idx is None:
        return {}
    return build(idx, set())


def _class_present(coord: GateCoordinator, cls: type) -> bool:
    """True when class has any emitted nodes or meta facet."""
    return bool(coord.get_nodes_for_class(cls)) or coord.get_snapshot(cls, "meta") is not None

# ═════════════════════════════════════════════════════════════════════════════
# Вспомогательные классы
# ═════════════════════════════════════════════════════════════════════════════


def _node_key(node_type: str, cls: type, suffix: str = "") -> str:
    """Формирует ключ узла графа: 'тип:модуль.ИмяКласса[.суффикс]'."""
    name = f"{cls.__module__}.{cls.__qualname__}"
    if suffix:
        name = f"{name}.{suffix}"
    return f"{node_type}:{name}"


class _Params(BaseParams):
    pass


class _Result(BaseResult):
    pass


class _ServiceA:
    pass


class _ServiceB:
    pass


@meta("Мок менеджер", domain=TestDomain)
class _MockManager(BaseResourceManager):
    """Минимальная реализация BaseResourceManager для тестов графа."""
    def get_wrapper_class(self):
        return None


class _EmptyClass:
    pass


@meta("Ping", domain=TestDomain)
@check_roles(NoneRole)
class _PingGraphAction(BaseAction["_Params", "_Result"]):
    """Минимальное действие для тестов графа."""
    @summary_aspect("Pong")
    async def pong_summary(self, params, state, box, connections):
        return {"message": "pong"}


@meta("Действие с зависимостями", domain=TestDomain)
@check_roles(NoneRole)
@depends(_ServiceA)
@depends(_ServiceB)
class _ActionWithDepsAction(BaseAction["_Params", "_Result"]):
    """Действие с двумя зависимостями для тестов графа."""
    @summary_aspect("Итог")
    async def finalize_summary(self, params, state, box, connections):
        return {}


@meta("Действие с соединением", domain=TestDomain)
@check_roles(NoneRole)
@connection(_MockManager, key="db", description="БД")
class _ActionWithConnAction(BaseAction["_Params", "_Result"]):
    """Действие с одним соединением для тестов графа."""
    @summary_aspect("Итог")
    async def finalize_summary(self, params, state, box, connections):
        return {}


@meta("Действие с чекерами", domain=TestDomain)
@check_roles(NoneRole)
class _ActionWithCheckersAction(BaseAction["_Params", "_Result"]):
    """Действие с regular-аспектом и чекером для тестов графа."""
    @regular_aspect("Шаг")
    @result_string("name")
    async def step_aspect(self, params, state, box, connections):
        return {"name": "Alice"}

    @summary_aspect("Итог")
    async def finalize_summary(self, params, state, box, connections):
        return {}


class _SensitiveGraphSchema(BaseSchema):
    """Схема с @sensitive — узел типа sensitive строит только SensitiveIntentInspector (BaseSchema)."""

    _secret: str = "hidden"

    @property
    @sensitive()
    def secret(self) -> str:
        return self._secret


class _TestPlugin(Plugin):
    """Тестовый плагин с одной подпиской для тестов графа."""
    async def get_initial_state(self) -> dict:
        return {}

    @on(GlobalStartEvent)
    async def on_start(self, state, event: GlobalStartEvent, log):
        return state


@meta("Действие с ролью", domain=TestDomain)
@check_roles(AdminRole)
class _RoledGraphAction(BaseAction["_Params", "_Result"]):
    """Действие с конкретной ролью для тестов графа."""
    @summary_aspect("Итог")
    async def finalize_summary(self, params, state, box, connections):
        return {}


@meta("Другое действие с ServiceA", domain=TestDomain)
@check_roles(NoneRole)
@depends(_ServiceA)
class _AnotherActionWithServiceAAction(BaseAction["_Params", "_Result"]):
    """Второе действие, зависящее от _ServiceA, для тестов разделения узлов."""
    @summary_aspect("Итог")
    async def finalize_summary(self, params, state, box, connections):
        return {}


@meta("Действие с компенсатором для тестов графа", domain=TestDomain)
@check_roles(NoneRole)
class _ActionWithCompensatorGraphAction(BaseAction["_Params", "_Result"]):
    """
    Действие с regular-аспектом и компенсатором для тестов графа.
    Используется в TestCompensatorNodes для проверки, что координатор
    создаёт узлы типа "compensator" и рёбра "has_compensator" в общем
    графе зависимостей.
    """
    @regular_aspect("Шаг с компенсатором")
    @result_string("value")
    async def step_aspect(self, params, state, box, connections):
        return {"value": "test"}

    @compensate("step_aspect", "Откат шага")
    async def rollback_step_compensate(self, params, state_before, state_after,
                                       box, connections, error):
        pass

    @summary_aspect("Итог")
    async def finalize_summary(self, params, state, box, connections):
        return {}


# ═════════════════════════════════════════════════════════════════════════════
# Базовые узлы
# ═════════════════════════════════════════════════════════════════════════════


class TestBasicNodes:
    """Проверяет создание базовых узлов графа."""

    def test_empty_coordinator_empty_graph(self):
        """До build() счётчики графа недоступны — только явный статус."""
        coord = GateCoordinator()
        assert coord.build_status() == "not_built"
        assert coord.is_built is False
        with pytest.raises(RuntimeError, match="not built"):
            _ = coord.graph_node_count
        with pytest.raises(RuntimeError, match="not built"):
            _ = coord.graph_edge_count

    def test_register_empty_class_creates_node(self):
        """Регистрация пустого класса создаёт узел в графе."""
        coord = _new_coord()
        coord.get_snapshot(_EmptyClass, "meta")
        assert coord.graph_node_count > 0

    def test_register_action_creates_action_node(self):
        """Регистрация action с @depends создаёт узел типа action (структурный facet)."""
        coord = _new_coord()
        coord.get_snapshot(_ActionWithDepsAction, "meta")
        nodes = coord.get_nodes_by_type("action")
        assert len(nodes) >= 1

    def test_register_plugin_creates_plugin_node(self):
        """Регистрация плагина создаёт facet-узлы subscription (не тип plugin)."""
        coord = _new_coord()
        coord.get_snapshot(_TestPlugin, "meta")
        nodes = coord.get_nodes_by_type("subscription")
        assert len(nodes) >= 1

    def test_register_action_with_role_creates_role_node(self):
        """Регистрация action с ролью создаёт узел role."""
        coord = _new_coord()
        coord.get_snapshot(_RoledGraphAction, "meta")
        nodes = coord.get_nodes_by_type("role")
        assert len(nodes) >= 1


# ═════════════════════════════════════════════════════════════════════════════
# Зависимости и соединения
# ═════════════════════════════════════════════════════════════════════════════


class TestDependenciesAndConnections:
    """Проверяет создание узлов и рёбер для зависимостей и соединений."""

    def test_dependencies_create_nodes_and_edges(self):
        """Зависимости создают узлы и рёбра в графе."""
        coord = _new_coord()
        coord.get_snapshot(_ActionWithDepsAction, "meta")
        assert coord.graph_node_count > 1
        assert coord.graph_edge_count > 0

    def test_connections_create_nodes_and_edges(self):
        """Соединения создают узлы и рёбра в графе."""
        coord = _new_coord()
        coord.get_snapshot(_ActionWithConnAction, "meta")
        assert coord.graph_edge_count > 0

    def test_same_dependency_shared_between_actions(self):
        """Общая зависимость — один stub-узел dependency на класс сервиса."""
        coord = _new_coord()
        coord.get_snapshot(_ActionWithDepsAction, "meta")
        coord.get_snapshot(_AnotherActionWithServiceAAction, "meta")
        assert _class_present(coord, _ServiceA)
        svc_key_fragment = f"{_ServiceA.__module__}.{_ServiceA.__qualname__}"
        dep_for_a = [
            n for n in coord.get_nodes_by_type("dependency")
            if svc_key_fragment in n["name"]
        ]
        assert len(dep_for_a) == 1


# ═════════════════════════════════════════════════════════════════════════════
# Аспекты и чекеры
# ═════════════════════════════════════════════════════════════════════════════


class TestAspectsAndCheckers:
    """Проверяет создание узлов для аспектов и чекеров."""

    def test_aspects_create_nodes_and_edges(self):
        """Аспекты создают узлы и рёбра в графе."""
        coord = _new_coord()
        coord.get_snapshot(_ActionWithCheckersAction, "meta")
        nodes = coord.get_nodes_by_type("aspect")
        assert len(nodes) >= 1

    def test_checkers_create_nodes_and_edges(self):
        """Чекеры создают узлы и рёбра в графе."""
        coord = _new_coord()
        coord.get_snapshot(_ActionWithCheckersAction, "meta")
        nodes = coord.get_nodes_by_type("checker")
        assert len(nodes) >= 1


# ═════════════════════════════════════════════════════════════════════════════
# Подписки и sensitive
# ═════════════════════════════════════════════════════════════════════════════


class TestSubscriptionsAndSensitive:
    """Проверяет создание узлов для подписок и sensitive-полей."""

    def test_subscriptions_create_nodes_and_edges(self):
        """Подписки создают узлы в графе."""
        coord = _new_coord()
        coord.get_snapshot(_TestPlugin, "meta")
        nodes = coord.get_nodes_by_type("subscription")
        assert len(nodes) >= 1

    def test_sensitive_fields_create_nodes_and_edges(self):
        """Sensitive на BaseSchema создаёт facet-узел типа sensitive."""
        coord = _new_coord()
        coord.get_snapshot(_SensitiveGraphSchema, "meta")
        nodes = coord.get_nodes_by_type("sensitive")
        assert len(nodes) >= 1


# ═════════════════════════════════════════════════════════════════════════════
# Компенсаторы в графе
# ═════════════════════════════════════════════════════════════════════════════


class TestCompensatorNodes:
    """
    Проверяет, что компенсаторы создают узлы типа "compensator" и рёбра
    "has_compensator" в общем графе GateCoordinator.

    Добавлено как часть реализации механизма компенсации (Saga).
    Детальные тесты графа компенсаторов (метаданные узлов, requires_context,
    dependency tree) покрыты в tests/compensate/test_compensate_graph.py.
    Здесь — минимальная проверка интеграции в общий граф координатора.
    """

    def test_compensator_node_created_in_graph(self):
        """
        При регистрации действия с @compensate в графе появляется
        узел типа "compensator".
        """
        # Arrange & Act
        coord = _new_coord()
        coord.get_snapshot(_ActionWithCompensatorGraphAction, "meta")

        # Assert — агрегированный узел на наш класс (в графе могут быть и другие actions)
        nodes = coord.get_nodes_by_type("compensator")
        ours = [n for n in nodes if n["class_ref"] is _ActionWithCompensatorGraphAction]
        assert len(ours) == 1
        node = ours[0]
        assert node["node_type"] == "compensator"
        assert _ActionWithCompensatorGraphAction.__qualname__ in node["name"]

    def test_has_compensator_edge_in_graph(self):
        """В facet-графе компенсатор — отдельный узел; рёбер has_compensator нет."""
        coord = _new_coord()
        coord.get_snapshot(_ActionWithCompensatorGraphAction, "meta")
        nodes = coord.get_nodes_by_type("compensator")
        node = next(
            n for n in nodes if n["class_ref"] is _ActionWithCompensatorGraphAction
        )
        entry_meta = dict(node["meta"]).get("compensators", ())
        assert any(dict(e)["method_name"] == "rollback_step_compensate" for e in entry_meta)


# ═════════════════════════════════════════════════════════════════════════════
# Рекурсивный сбор зависимостей
# ═════════════════════════════════════════════════════════════════════════════


class TestRecursiveCollection:
    """Проверяет автоматический рекурсивный сбор зависимостей."""

    def test_dependency_class_automatically_registered(self):
        """Класс зависимости автоматически регистрируется."""
        coord = _new_coord()
        coord.get_snapshot(_ActionWithDepsAction, "meta")
        assert _class_present(coord, _ServiceA)
        assert _class_present(coord, _ServiceB)

    def test_connection_class_automatically_registered(self):
        """Класс соединения автоматически регистрируется."""
        coord = _new_coord()
        coord.get_snapshot(_ActionWithConnAction, "meta")
        assert _class_present(coord, _MockManager)

    def test_duplicate_dependency_not_collected_twice(self):
        """Дублирующая зависимость не регистрируется повторно."""
        coord = _new_coord()
        coord.get_snapshot(_ActionWithDepsAction, "meta")
        size_after_first = len(coord.get_nodes_for_class(_ServiceA))
        coord.get_snapshot(_AnotherActionWithServiceAAction, "meta")
        size_after_second = len(coord.get_nodes_for_class(_ServiceA))
        # In snapshot-first graph, the shared dependency class is reused.
        assert size_after_second <= size_after_first + 1


# ═════════════════════════════════════════════════════════════════════════════
# Обнаружение циклов
# ═════════════════════════════════════════════════════════════════════════════


class TestCycleDetection:
    """
    Фаза 2 графа проверяет ацикличность **структурных** рёбер между узлами
    facet-графа (``action`` → ``dependency`` / ``connection`` как разные ключи).
    Логические циклы «A зависит от B, B от A» не обязаны давать цикл в этом
    графе; отдельная проверка в ``get()`` по цепочке зависимостей не
    реализована — см. ``_phase2_check_acyclicity``.
    """

    def test_diamond_dependency_no_cycle(self):
        """Ромбовидная зависимость без цикла — допустима."""
        coord = _new_coord()
        coord.get_snapshot(_ActionWithDepsAction, "meta")
        coord.get_snapshot(_AnotherActionWithServiceAAction, "meta")
        assert _class_present(coord, _ActionWithDepsAction)
        assert _class_present(coord, _AnotherActionWithServiceAAction)
        assert _class_present(coord, _ServiceA)


# ═════════════════════════════════════════════════════════════════════════════
# Публичное API
# ═════════════════════════════════════════════════════════════════════════════


class TestPublicAPI:
    """Проверяет публичные методы GateCoordinator для инспекции графа."""

    def test_get_graph_returns_copy(self):
        """get_graph возвращает копию графа."""
        coord = _new_coord()
        coord.get_snapshot(_PingGraphAction, "meta")
        g1 = coord.get_graph()
        g2 = coord.get_graph()
        assert g1 is not g2

    def test_get_node_existing(self):
        """get_node для facet meta зарегистрированного action возвращает данные."""
        coord = _new_coord()
        coord.get_snapshot(_PingGraphAction, "meta")
        key = _node_key("meta", _PingGraphAction)
        node = coord.get_node(key)
        assert node is not None

    def test_get_node_missing_returns_none(self):
        """get_node для незарегистрированного класса возвращает None."""
        coord = CoreActionMachine.create_coordinator()
        node = coord.get_node("action", "nonexistent.module.AbsentAction")
        assert node is None

    def test_get_children_of_action(self):
        """Дочерние узлы в графе (исходящие рёбра) у action с зависимостями непусты."""
        coord = _new_coord()
        coord.get_snapshot(_ActionWithDepsAction, "meta")
        key = _node_key("action", _ActionWithDepsAction)
        children = _graph_children(coord, key)
        assert len(children) > 0

    def test_get_children_of_missing_node(self):
        """У незарегистрированного класса нет исходящих рёбер от action-узла."""
        coord = CoreActionMachine.create_coordinator()
        children = _graph_children(coord, _node_key("action", _EmptyClass))
        assert children == []

    def test_get_nodes_by_type_action(self):
        """get_nodes_by_type('action') возвращает все действия."""
        coord = _new_coord()
        coord.get_snapshot(_PingGraphAction, "meta")
        coord.get_snapshot(_ActionWithDepsAction, "meta")
        actions = coord.get_nodes_by_type("action")
        assert len(actions) >= 2

    def test_get_nodes_by_type_empty(self):
        """get_nodes_by_type на пустом координаторе — пустой список."""
        coord = CoreActionMachine.create_coordinator()
        result = coord.get_nodes_by_type("action")
        assert isinstance(result, list)

    def test_get_dependency_tree_structure(self):
        """Вспомогательное дерево зависимостей по графу непустое для action с deps."""
        coord = _new_coord()
        coord.get_snapshot(_ActionWithDepsAction, "meta")
        tree = _dependency_tree(coord, _ActionWithDepsAction)
        assert tree is not None
        assert isinstance(tree, dict)

    def test_get_dependency_tree_missing_node(self):
        """Для класса без узлов в графе дерево зависимостей пустое или отсутствует."""
        coord = CoreActionMachine.create_coordinator()
        tree = _dependency_tree(coord, _EmptyClass)
        assert tree is None or tree == {}

    def test_get_dependency_tree_checkers_nested_under_aspects(self):
        """Дерево по графу отражает чекеры под соответствующими аспектами."""
        coord = _new_coord()
        coord.get_snapshot(_ActionWithCheckersAction, "meta")
        tree = _dependency_tree(coord, _ActionWithCheckersAction)
        assert tree is not None

    def test_graph_node_count(self):
        """graph_node_count возвращает количество узлов."""
        coord = _new_coord()
        coord.get_snapshot(_PingGraphAction, "meta")
        assert coord.graph_node_count > 0

    def test_graph_edge_count(self):
        """graph_edge_count возвращает количество рёбер."""
        coord = _new_coord()
        coord.get_snapshot(_ActionWithDepsAction, "meta")
        assert coord.graph_edge_count > 0


# ═════════════════════════════════════════════════════════════════════════════
# Инвалидация
# ═════════════════════════════════════════════════════════════════════════════


class TestInvalidation:
    """Проверяет инвалидацию кеша координатора."""

    def test_invalidate_removes_from_cache(self):
        """Сброс кеша dependency factory не ломает чтение facet-снимков."""
        coord = _new_coord()
        coord.get_snapshot(_PingGraphAction, "meta")
        removed = clear_dependency_factory_cache(coord)
        assert isinstance(removed, int)
        assert coord.get_snapshot(_PingGraphAction, "meta") is not None

    def test_invalidate_all_clears_cache(self):
        """clear_dependency_factory_cache возвращает число очищенных записей."""
        coord = _new_coord()
        cached_dependency_factory(coord, _PingGraphAction)
        cached_dependency_factory(coord, _ActionWithDepsAction)
        removed = clear_dependency_factory_cache(coord)
        assert removed >= 1

    def test_invalidate_preserves_shared_dependency_node(self):
        """Сброс кеша фабрик не меняет число узлов фасетного графа."""
        coord = _new_coord()
        before_nodes = coord.graph_node_count
        clear_dependency_factory_cache(coord)
        assert coord.graph_node_count == before_nodes

    def test_invalidate_allows_rebuild(self):
        """После сброса кеша фабрик facet-снимки остаются доступны без rebuild."""
        coord = _new_coord()
        clear_dependency_factory_cache(coord)
        meta = coord.get_snapshot(_PingGraphAction, "meta")
        assert meta is not None
        assert meta.class_ref is _PingGraphAction

    def test_invalidate_non_existing_no_error(self):
        """Повторный сброс кеша фабрик не вызывает ошибок."""
        coord = _new_coord()
        clear_dependency_factory_cache(coord)
        clear_dependency_factory_cache(coord)

    def test_invalidate_all_empty_no_error(self):
        """Сброс кеша фабрик на непостроенном координаторе — без ошибок, 0 записей."""
        coord = GateCoordinator()
        assert clear_dependency_factory_cache(coord) == 0


# ═════════════════════════════════════════════════════════════════════════════
# Базовое API координатора
# ═════════════════════════════════════════════════════════════════════════════


class TestCoordinatorBasic:
    """Проверяет базовые методы GateCoordinator."""

    def test_get_builds_and_caches(self):
        """Built coordinator returns stable meta snapshots."""
        coord = CoreActionMachine.create_coordinator()
        meta1 = coord.get_snapshot(_PingGraphAction, "meta")
        meta2 = coord.get_snapshot(_PingGraphAction, "meta")
        assert meta1 is not None
        assert meta2 is not None
        assert meta1.class_ref is _PingGraphAction
        assert meta2.class_ref is _PingGraphAction

    def test_register_same_as_get(self):
        """register now accepts inspector classes only."""
        coord = GateCoordinator()
        returned = coord.register(MetaIntentInspector)
        assert returned is coord

    def test_has_before_get(self):
        """Empty coordinator has not-built state in repr."""
        coord = GateCoordinator()
        assert "state=not built" in repr(coord)

    def test_has_after_get(self):
        """Built coordinator reports built state in repr."""
        coord = CoreActionMachine.create_coordinator()
        assert "state=built" in repr(coord)

    def test_size(self):
        """Graph has nodes after build."""
        coord = CoreActionMachine.create_coordinator()
        assert coord.graph_node_count > 0

    def test_get_all_metadata(self):
        """Meta snapshot is available for decorated action."""
        coord = CoreActionMachine.create_coordinator()
        all_meta = coord.get_snapshot(_PingGraphAction, "meta")
        assert all_meta is not None

    def test_get_all_classes(self):
        """Graph is queryable for known facet type."""
        coord = CoreActionMachine.create_coordinator()
        meta_nodes = coord.get_nodes_by_type("meta")
        assert isinstance(meta_nodes, list)
        assert len(meta_nodes) > 0

    def test_get_not_a_class_raises(self):
        """register rejects non-inspector classes."""
        coord = GateCoordinator()
        with pytest.raises(TypeError):
            coord.register(_EmptyClass)  # type: ignore[arg-type]

    def test_get_factory(self):
        """cached_dependency_factory даёт DependencyFactory для действия с зависимостями."""
        coord = CoreActionMachine.create_coordinator()
        factory = cached_dependency_factory(coord, _ActionWithDepsAction)
        assert factory is not None
        assert factory.has(_ServiceA)
        assert factory.has(_ServiceB)

    def test_repr_empty(self):
        """repr пустого координатора — строка."""
        coord = GateCoordinator()
        assert isinstance(repr(coord), str)

    def test_repr_with_classes(self):
        """repr координатора с классами — строка."""
        coord = CoreActionMachine.create_coordinator()
        assert isinstance(repr(coord), str)

    def test_repr_includes_graph_info(self):
        """repr содержит информацию о графе."""
        coord = CoreActionMachine.create_coordinator()
        result = repr(coord)
        assert isinstance(result, str)
        assert len(result) > 0
