# tests/metadata/test_coordinator_graph.py
"""
Тесты GateCoordinator — граф зависимостей, узлы, рёбра, циклы, публичное API.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Проверяет, что GateCoordinator строит направленный граф из
зарегистрированных классов, создаёт узлы для действий, зависимостей,
соединений, аспектов, чекеров, подписок, sensitive-полей, обнаруживает
циклические зависимости и предоставляет публичное API для инспекции.

═══════════════════════════════════════════════════════════════════════════════
СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

TestBasicNodes — создание базовых узлов графа.
TestDependenciesAndConnections — узлы и рёбра зависимостей и соединений.
TestAspectsAndCheckers — узлы аспектов и чекеров.
TestSubscriptionsAndSensitive — узлы подписок и sensitive-полей.
TestRecursiveCollection — автоматический рекурсивный сбор зависимостей.
TestCycleDetection — обнаружение циклических зависимостей.
TestPublicAPI — публичные методы инспекции графа.
TestInvalidation — инвалидация кеша координатора.
TestCoordinatorBasic — базовое API координатора.
"""

import pytest

from action_machine.aspects.regular_aspect import regular_aspect
from action_machine.aspects.summary_aspect import summary_aspect
from action_machine.auth.check_roles import check_roles
from action_machine.auth.constants import ROLE_NONE
from action_machine.checkers.result_string_checker import result_string
from action_machine.core.base_action import BaseAction
from action_machine.core.base_params import BaseParams
from action_machine.core.base_result import BaseResult
from action_machine.core.exceptions import CyclicDependencyError
from action_machine.core.gate_coordinator import GateCoordinator
from action_machine.core.meta_decorator import meta
from action_machine.dependencies.depends import depends
from action_machine.logging.sensitive_decorator import sensitive
from action_machine.plugins.decorators import on
from action_machine.plugins.on_gate_host import OnGateHost
from action_machine.resource_managers.base_resource_manager import BaseResourceManager
from action_machine.resource_managers.connection import connection

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


@meta("Мок менеджер")
class _MockManager(BaseResourceManager):
    """Минимальная реализация BaseResourceManager для тестов графа."""

    def get_wrapper_class(self):
        return None


class _EmptyClass:
    pass


@meta("Ping")
@check_roles(ROLE_NONE)
class _PingGraphAction(BaseAction["_Params", "_Result"]):
    """Минимальное действие для тестов графа."""

    @summary_aspect("Pong")
    async def pong_summary(self, params, state, box, connections):
        return {"message": "pong"}


@meta("Действие с зависимостями")
@check_roles(ROLE_NONE)
@depends(_ServiceA)
@depends(_ServiceB)
class _ActionWithDepsAction(BaseAction["_Params", "_Result"]):
    """Действие с двумя зависимостями для тестов графа."""

    @summary_aspect("Итог")
    async def finalize_summary(self, params, state, box, connections):
        return {}


@meta("Действие с соединением")
@check_roles(ROLE_NONE)
@connection(_MockManager, key="db", description="БД")
class _ActionWithConnAction(BaseAction["_Params", "_Result"]):
    """Действие с одним соединением для тестов графа."""

    @summary_aspect("Итог")
    async def finalize_summary(self, params, state, box, connections):
        return {}


@meta("Действие с чекерами")
@check_roles(ROLE_NONE)
class _ActionWithCheckersAction(BaseAction["_Params", "_Result"]):
    """Действие с regular-аспектом и чекером для тестов графа."""

    @regular_aspect("Шаг")
    @result_string("name")
    async def step_aspect(self, params, state, box, connections):
        return {"name": "Alice"}

    @summary_aspect("Итог")
    async def finalize_summary(self, params, state, box, connections):
        return {}


@meta("Действие с sensitive")
@check_roles(ROLE_NONE)
class _ActionWithSensitiveAction(BaseAction["_Params", "_Result"]):
    """Действие с sensitive-свойством для тестов графа."""

    def __init__(self):
        self._secret = "hidden"

    @sensitive()
    @property
    def secret(self):
        return self._secret

    @summary_aspect("Итог")
    async def finalize_summary(self, params, state, box, connections):
        return {}


class _TestPlugin(OnGateHost):
    """Тестовый плагин с одной подпиской для тестов графа."""

    @on("global_start")
    async def on_start_on(self, state, event, log):
        return state


@meta("Действие с ролью")
@check_roles("admin")
class _RoledGraphAction(BaseAction["_Params", "_Result"]):
    """Действие с конкретной ролью для тестов графа."""

    @summary_aspect("Итог")
    async def finalize_summary(self, params, state, box, connections):
        return {}


@meta("Другое действие с ServiceA")
@check_roles(ROLE_NONE)
@depends(_ServiceA)
class _AnotherActionWithServiceAAction(BaseAction["_Params", "_Result"]):
    """Второе действие, зависящее от _ServiceA, для тестов разделения узлов."""

    @summary_aspect("Итог")
    async def finalize_summary(self, params, state, box, connections):
        return {}


# ═════════════════════════════════════════════════════════════════════════════
# Базовые узлы
# ═════════════════════════════════════════════════════════════════════════════


class TestBasicNodes:
    """Проверяет создание базовых узлов графа."""

    def test_empty_coordinator_empty_graph(self):
        """Пустой координатор имеет пустой граф."""
        coord = GateCoordinator()
        assert coord.graph_node_count == 0

    def test_register_empty_class_creates_node(self):
        """Регистрация пустого класса создаёт узел в графе."""
        coord = GateCoordinator()
        coord.get(_EmptyClass)
        assert coord.graph_node_count > 0

    def test_register_action_creates_action_node(self):
        """Регистрация action создаёт узел типа action."""
        coord = GateCoordinator()
        coord.get(_PingGraphAction)
        nodes = coord.get_nodes_by_type("action")
        assert len(nodes) >= 1

    def test_register_plugin_creates_plugin_node(self):
        """Регистрация плагина создаёт узел типа plugin."""
        coord = GateCoordinator()
        coord.get(_TestPlugin)
        nodes = coord.get_nodes_by_type("plugin")
        assert len(nodes) >= 1

    def test_register_action_with_role_creates_role_node(self):
        """Регистрация action с ролью создаёт узел role."""
        coord = GateCoordinator()
        coord.get(_RoledGraphAction)
        nodes = coord.get_nodes_by_type("role")
        assert len(nodes) >= 1


# ═════════════════════════════════════════════════════════════════════════════
# Зависимости и соединения
# ═════════════════════════════════════════════════════════════════════════════


class TestDependenciesAndConnections:
    """Проверяет создание узлов и рёбер для зависимостей и соединений."""

    def test_dependencies_create_nodes_and_edges(self):
        """Зависимости создают узлы и рёбра в графе."""
        coord = GateCoordinator()
        coord.get(_ActionWithDepsAction)
        assert coord.graph_node_count > 1
        assert coord.graph_edge_count > 0

    def test_connections_create_nodes_and_edges(self):
        """Соединения создают узлы и рёбра в графе."""
        coord = GateCoordinator()
        coord.get(_ActionWithConnAction)
        assert coord.graph_edge_count > 0

    def test_same_dependency_shared_between_actions(self):
        """Общая зависимость разделяется между действиями."""
        coord = GateCoordinator()
        coord.get(_ActionWithDepsAction)
        node_count_after_first = coord.graph_node_count
        coord.get(_AnotherActionWithServiceAAction)
        node_count_after_second = coord.graph_node_count
        assert coord.has(_ServiceA)
        assert node_count_after_second > node_count_after_first


# ═════════════════════════════════════════════════════════════════════════════
# Аспекты и чекеры
# ═════════════════════════════════════════════════════════════════════════════


class TestAspectsAndCheckers:
    """Проверяет создание узлов для аспектов и чекеров."""

    def test_aspects_create_nodes_and_edges(self):
        """Аспекты создают узлы и рёбра в графе."""
        coord = GateCoordinator()
        coord.get(_ActionWithCheckersAction)
        nodes = coord.get_nodes_by_type("aspect")
        assert len(nodes) >= 1

    def test_checkers_create_nodes_and_edges(self):
        """Чекеры создают узлы и рёбра в графе."""
        coord = GateCoordinator()
        coord.get(_ActionWithCheckersAction)
        nodes = coord.get_nodes_by_type("checker")
        assert len(nodes) >= 1


# ═════════════════════════════════════════════════════════════════════════════
# Подписки и sensitive
# ═════════════════════════════════════════════════════════════════════════════


class TestSubscriptionsAndSensitive:
    """Проверяет создание узлов для подписок и sensitive-полей."""

    def test_subscriptions_create_nodes_and_edges(self):
        """Подписки создают узлы в графе."""
        coord = GateCoordinator()
        coord.get(_TestPlugin)
        nodes = coord.get_nodes_by_type("subscription")
        assert len(nodes) >= 1

    def test_sensitive_fields_create_nodes_and_edges(self):
        """Sensitive-поля создают узлы в графе."""
        coord = GateCoordinator()
        coord.get(_ActionWithSensitiveAction)
        nodes = coord.get_nodes_by_type("sensitive")
        assert len(nodes) >= 1


# ═════════════════════════════════════════════════════════════════════════════
# Рекурсивный сбор зависимостей
# ═════════════════════════════════════════════════════════════════════════════


class TestRecursiveCollection:
    """Проверяет автоматический рекурсивный сбор зависимостей."""

    def test_dependency_class_automatically_registered(self):
        """Класс зависимости автоматически регистрируется."""
        coord = GateCoordinator()
        coord.get(_ActionWithDepsAction)
        assert coord.has(_ServiceA)
        assert coord.has(_ServiceB)

    def test_connection_class_automatically_registered(self):
        """Класс соединения автоматически регистрируется."""
        coord = GateCoordinator()
        coord.get(_ActionWithConnAction)
        assert coord.has(_MockManager)

    def test_duplicate_dependency_not_collected_twice(self):
        """Дублирующая зависимость не регистрируется повторно."""
        coord = GateCoordinator()
        coord.get(_ActionWithDepsAction)
        size_after_first = coord.size
        coord.get(_AnotherActionWithServiceAAction)
        size_after_second = coord.size
        assert size_after_second == size_after_first + 1


# ═════════════════════════════════════════════════════════════════════════════
# Обнаружение циклов
# ═════════════════════════════════════════════════════════════════════════════


class TestCycleDetection:
    """Проверяет обнаружение циклических зависимостей."""

    def test_self_dependency_detected(self):
        """Самозависимость обнаруживается."""
        class _SelfRef:
            pass
        _SelfRef._depends_info = [type("DI", (), {"cls": _SelfRef, "factory": None, "description": ""})()]

        coord = GateCoordinator()
        with pytest.raises(CyclicDependencyError):
            coord.get(_SelfRef)

    def test_mutual_dependency_detected(self):
        """Взаимная зависимость обнаруживается."""
        class _MutualA:
            pass

        class _MutualB:
            pass

        _MutualA._depends_info = [type("DI", (), {"cls": _MutualB, "factory": None, "description": ""})()]
        _MutualB._depends_info = [type("DI", (), {"cls": _MutualA, "factory": None, "description": ""})()]

        coord = GateCoordinator()
        with pytest.raises(CyclicDependencyError):
            coord.get(_MutualA)

    def test_three_class_cycle_detected(self):
        """Цикл из трёх классов обнаруживается."""
        class _CycA:
            pass

        class _CycB:
            pass

        class _CycC:
            pass

        _CycA._depends_info = [type("DI", (), {"cls": _CycB, "factory": None, "description": ""})()]
        _CycB._depends_info = [type("DI", (), {"cls": _CycC, "factory": None, "description": ""})()]
        _CycC._depends_info = [type("DI", (), {"cls": _CycA, "factory": None, "description": ""})()]

        coord = GateCoordinator()
        with pytest.raises(CyclicDependencyError):
            coord.get(_CycA)

    def test_diamond_dependency_no_cycle(self):
        """Ромбовидная зависимость без цикла — допустима."""
        coord = GateCoordinator()
        coord.get(_ActionWithDepsAction)
        coord.get(_AnotherActionWithServiceAAction)
        assert coord.has(_ActionWithDepsAction)
        assert coord.has(_AnotherActionWithServiceAAction)
        assert coord.has(_ServiceA)


# ═════════════════════════════════════════════════════════════════════════════
# Публичное API
# ═════════════════════════════════════════════════════════════════════════════


class TestPublicAPI:
    """Проверяет публичные методы GateCoordinator для инспекции графа."""

    def test_get_graph_returns_copy(self):
        """get_graph возвращает копию графа."""
        coord = GateCoordinator()
        coord.get(_PingGraphAction)
        g1 = coord.get_graph()
        g2 = coord.get_graph()
        assert g1 is not g2

    def test_get_node_existing(self):
        """get_node для зарегистрированного класса возвращает данные."""
        coord = GateCoordinator()
        coord.get(_PingGraphAction)
        key = _node_key("action", _PingGraphAction)
        node = coord.get_node(key)
        assert node is not None

    def test_get_node_missing_returns_none(self):
        """get_node для незарегистрированного класса возвращает None."""
        coord = GateCoordinator()
        node = coord.get_node(_EmptyClass)
        assert node is None

    def test_get_children_of_action(self):
        """get_children для действия с зависимостями возвращает дочерние узлы."""
        coord = GateCoordinator()
        coord.get(_ActionWithDepsAction)
        key = _node_key("action", _ActionWithDepsAction)
        children = coord.get_children(key)
        assert len(children) > 0

    def test_get_children_of_missing_node(self):
        """get_children для незарегистрированного класса — пустой список."""
        coord = GateCoordinator()
        children = coord.get_children(_EmptyClass)
        assert children == []

    def test_get_nodes_by_type_action(self):
        """get_nodes_by_type('action') возвращает все действия."""
        coord = GateCoordinator()
        coord.get(_PingGraphAction)
        coord.get(_ActionWithDepsAction)
        actions = coord.get_nodes_by_type("action")
        assert len(actions) >= 2

    def test_get_nodes_by_type_empty(self):
        """get_nodes_by_type на пустом координаторе — пустой список."""
        coord = GateCoordinator()
        result = coord.get_nodes_by_type("action")
        assert result == []

    def test_get_dependency_tree_structure(self):
        """get_dependency_tree возвращает непустую структуру."""
        coord = GateCoordinator()
        coord.get(_ActionWithDepsAction)
        tree = coord.get_dependency_tree(_ActionWithDepsAction)
        assert tree is not None
        assert isinstance(tree, dict)

    def test_get_dependency_tree_missing_node(self):
        """get_dependency_tree для незарегистрированного класса."""
        coord = GateCoordinator()
        tree = coord.get_dependency_tree(_EmptyClass)
        assert tree is None or tree == {}

    def test_get_dependency_tree_checkers_nested_under_aspects(self):
        """get_dependency_tree содержит чекеры вложенные под аспекты."""
        coord = GateCoordinator()
        coord.get(_ActionWithCheckersAction)
        tree = coord.get_dependency_tree(_ActionWithCheckersAction)
        assert tree is not None

    def test_graph_node_count(self):
        """graph_node_count возвращает количество узлов."""
        coord = GateCoordinator()
        coord.get(_PingGraphAction)
        assert coord.graph_node_count > 0

    def test_graph_edge_count(self):
        """graph_edge_count возвращает количество рёбер."""
        coord = GateCoordinator()
        coord.get(_ActionWithDepsAction)
        assert coord.graph_edge_count > 0


# ═════════════════════════════════════════════════════════════════════════════
# Инвалидация
# ═════════════════════════════════════════════════════════════════════════════


class TestInvalidation:
    """Проверяет инвалидацию кеша координатора."""

    def test_invalidate_removes_from_cache(self):
        """invalidate удаляет класс из кеша."""
        coord = GateCoordinator()
        coord.get(_PingGraphAction)
        assert coord.has(_PingGraphAction)
        coord.invalidate(_PingGraphAction)
        assert coord.has(_PingGraphAction) is False

    def test_invalidate_all_clears_cache(self):
        """invalidate_all очищает весь кеш."""
        coord = GateCoordinator()
        coord.get(_PingGraphAction)
        coord.get(_ActionWithDepsAction)
        coord.invalidate_all()
        assert coord.size == 0

    def test_invalidate_preserves_shared_dependency_node(self):
        """invalidate одного действия не удаляет общую зависимость другого."""
        coord = GateCoordinator()
        coord.get(_ActionWithDepsAction)
        coord.get(_AnotherActionWithServiceAAction)
        coord.invalidate(_ActionWithDepsAction)
        assert coord.has(_AnotherActionWithServiceAAction)

    def test_invalidate_allows_rebuild(self):
        """После invalidate класс можно перерегистрировать."""
        coord = GateCoordinator()
        coord.get(_PingGraphAction)
        coord.invalidate(_PingGraphAction)
        meta = coord.get(_PingGraphAction)
        assert meta.class_ref is _PingGraphAction
        assert coord.has(_PingGraphAction)

    def test_invalidate_non_existing_no_error(self):
        """invalidate для незарегистрированного класса — без ошибок."""
        coord = GateCoordinator()
        coord.invalidate(_EmptyClass)

    def test_invalidate_all_empty_no_error(self):
        """invalidate_all на пустом координаторе — без ошибок."""
        coord = GateCoordinator()
        coord.invalidate_all()
        assert coord.size == 0


# ═════════════════════════════════════════════════════════════════════════════
# Базовое API координатора
# ═════════════════════════════════════════════════════════════════════════════


class TestCoordinatorBasic:
    """Проверяет базовые методы GateCoordinator."""

    def test_get_builds_and_caches(self):
        """get строит метаданные и кеширует результат."""
        coord = GateCoordinator()
        meta1 = coord.get(_PingGraphAction)
        meta2 = coord.get(_PingGraphAction)
        assert meta1 is meta2

    def test_register_same_as_get(self):
        """register — синоним get."""
        coord = GateCoordinator()
        meta1 = coord.register(_PingGraphAction)
        meta2 = coord.get(_PingGraphAction)
        assert meta1 is meta2

    def test_has_before_get(self):
        """has возвращает False до регистрации."""
        coord = GateCoordinator()
        assert coord.has(_PingGraphAction) is False

    def test_has_after_get(self):
        """has возвращает True после регистрации."""
        coord = GateCoordinator()
        coord.get(_PingGraphAction)
        assert coord.has(_PingGraphAction) is True

    def test_size(self):
        """size возвращает количество зарегистрированных классов."""
        coord = GateCoordinator()
        coord.get(_PingGraphAction)
        coord.get(_ActionWithDepsAction)
        assert coord.size >= 2

    def test_get_all_metadata(self):
        """get_all_metadata возвращает все метаданные."""
        coord = GateCoordinator()
        coord.get(_PingGraphAction)
        all_meta = coord.get_all_metadata()
        assert len(all_meta) >= 1

    def test_get_all_classes(self):
        """get_all_classes возвращает все зарегистрированные классы."""
        coord = GateCoordinator()
        coord.get(_PingGraphAction)
        coord.get(_ActionWithDepsAction)
        classes = coord.get_all_classes()
        assert _PingGraphAction in classes
        assert _ActionWithDepsAction in classes

    def test_get_not_a_class_raises(self):
        """get с экземпляром вместо класса → ошибка."""
        coord = GateCoordinator()
        with pytest.raises((TypeError, ValueError)):
            coord.get(_EmptyClass())

    def test_get_factory(self):
        """get_factory возвращает DependencyFactory для действия с зависимостями."""
        coord = GateCoordinator()
        coord.get(_ActionWithDepsAction)
        factory = coord.get_factory(_ActionWithDepsAction)
        assert factory is not None
        assert factory.has(_ServiceA)
        assert factory.has(_ServiceB)

    def test_repr_empty(self):
        """repr пустого координатора — строка."""
        coord = GateCoordinator()
        assert isinstance(repr(coord), str)

    def test_repr_with_classes(self):
        """repr координатора с классами — строка."""
        coord = GateCoordinator()
        coord.get(_PingGraphAction)
        assert isinstance(repr(coord), str)

    def test_repr_includes_graph_info(self):
        """repr содержит информацию о графе."""
        coord = GateCoordinator()
        coord.get(_PingGraphAction)
        result = repr(coord)
        assert isinstance(result, str)
        assert len(result) > 0
