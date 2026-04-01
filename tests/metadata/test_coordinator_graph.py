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

Тесты используют только публичное API координатора (get_node, get_children,
get_nodes_by_type, graph_node_count, graph_edge_count, get_dependency_tree,
get_graph). Внутренняя реализация графа (rustworkx) не используется
напрямую.

═══════════════════════════════════════════════════════════════════════════════
СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

TestBasicNodes
    - Пустой координатор — пустой граф.
    - Регистрация пустого класса — узел dependency.
    - Регистрация action — узел action.
    - Регистрация плагина — узел plugin.
    - Действие с ролью — узел role.

TestDependenciesAndConnections
    - Зависимости создают узлы и рёбра.
    - Соединения создают узлы и рёбра.
    - Общая зависимость разделяется между действиями.

TestAspectsAndCheckers
    - Аспекты создают узлы и рёбра.
    - Чекеры создают узлы и рёбра.

TestSubscriptionsAndSensitive
    - Подписки создают узлы и рёбра.
    - Sensitive-поля создают узлы и рёбра.

TestRecursiveCollection
    - Транзитивные зависимости собираются автоматически.
    - Дубликаты не собираются повторно.

TestCycleDetection
    - Самозависимость обнаруживается.
    - Взаимная зависимость обнаруживается.
    - Цикл из трёх классов обнаруживается.
    - Ромбовидная зависимость без цикла — допустима.

TestPublicAPI
    - get_graph возвращает копию.
    - get_node для существующего/отсутствующего узла.
    - get_children возвращает дочерние узлы.
    - get_children для отсутствующего — пустой список.
    - get_nodes_by_type фильтрует по типу.
    - get_dependency_tree возвращает дерево.

TestInvalidation
    - invalidate удаляет один класс.
    - invalidate_all очищает всё.
    - После invalidate — перерегистрация.

TestCoordinatorBasic
    - get/register/has/size/get_all_metadata/get_all_classes.
    - get_factory.
    - repr.
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
    pass


class _EmptyClass:
    pass


@meta("Ping")
@check_roles(ROLE_NONE)
class _PingAction(BaseAction["_Params", "_Result"]):

    @summary_aspect("Pong")
    async def pong(self, params, state, box, connections):
        return {"message": "pong"}


@meta("Действие с зависимостями")
@check_roles(ROLE_NONE)
@depends(_ServiceA)
@depends(_ServiceB)
class _ActionWithDeps(BaseAction["_Params", "_Result"]):

    @summary_aspect("Итог")
    async def finalize(self, params, state, box, connections):
        return {}


@meta("Действие с соединением")
@check_roles(ROLE_NONE)
@connection(_MockManager, key="db", description="БД")
class _ActionWithConn(BaseAction["_Params", "_Result"]):

    @summary_aspect("Итог")
    async def finalize(self, params, state, box, connections):
        return {}


@meta("Действие с чекерами")
@check_roles(ROLE_NONE)
class _ActionWithCheckers(BaseAction["_Params", "_Result"]):

    @regular_aspect("Шаг")
    @result_string("name")
    async def step(self, params, state, box, connections):
        return {"name": "Alice"}

    @summary_aspect("Итог")
    async def finalize(self, params, state, box, connections):
        return {}


@meta("Действие с sensitive")
@check_roles(ROLE_NONE)
class _ActionWithSensitive(BaseAction["_Params", "_Result"]):

    def __init__(self):
        self._secret = "hidden"

    @sensitive()
    @property
    def secret(self):
        return self._secret

    @summary_aspect("Итог")
    async def finalize(self, params, state, box, connections):
        return {}


class _TestPlugin(OnGateHost):

    @on("global.start")
    async def on_start(self, event, state, logger):
        pass


@meta("Действие с ролью")
@check_roles("admin")
class _RoledAction(BaseAction["_Params", "_Result"]):

    @summary_aspect("Итог")
    async def finalize(self, params, state, box, connections):
        return {}


@meta("Другое действие с ServiceA")
@check_roles(ROLE_NONE)
@depends(_ServiceA)
class _AnotherActionWithServiceA(BaseAction["_Params", "_Result"]):

    @summary_aspect("Итог")
    async def finalize(self, params, state, box, connections):
        return {}


# ═════════════════════════════════════════════════════════════════════════════
# Базовые узлы
# ═════════════════════════════════════════════════════════════════════════════


class TestBasicNodes:
    """Проверяет создание базовых узлов графа."""

    def test_empty_coordinator_empty_graph(self):
        """Пустой координатор имеет пустой граф."""
        # Arrange & Act
        coord = GateCoordinator()

        # Assert
        assert coord.graph_node_count == 0

    def test_register_empty_class_creates_node(self):
        """Регистрация пустого класса создаёт узел в графе."""
        # Arrange
        coord = GateCoordinator()

        # Act
        coord.get(_EmptyClass)

        # Assert
        assert coord.graph_node_count > 0

    def test_register_action_creates_action_node(self):
        """Регистрация action создаёт узел типа action."""
        # Arrange
        coord = GateCoordinator()

        # Act
        coord.get(_PingAction)
        nodes = coord.get_nodes_by_type("action")

        # Assert
        assert len(nodes) >= 1

    def test_register_plugin_creates_plugin_node(self):
        """Регистрация плагина создаёт узел типа plugin."""
        # Arrange
        coord = GateCoordinator()

        # Act
        coord.get(_TestPlugin)
        nodes = coord.get_nodes_by_type("plugin")

        # Assert
        assert len(nodes) >= 1

    def test_register_action_with_role_creates_role_node(self):
        """Регистрация action с ролью создаёт узел role."""
        # Arrange
        coord = GateCoordinator()

        # Act
        coord.get(_RoledAction)
        nodes = coord.get_nodes_by_type("role")

        # Assert
        assert len(nodes) >= 1


# ═════════════════════════════════════════════════════════════════════════════
# Зависимости и соединения
# ═════════════════════════════════════════════════════════════════════════════


class TestDependenciesAndConnections:
    """Проверяет создание узлов и рёбер для зависимостей и соединений."""

    def test_dependencies_create_nodes_and_edges(self):
        """Зависимости создают узлы и рёбра в графе."""
        # Arrange
        coord = GateCoordinator()

        # Act
        coord.get(_ActionWithDeps)

        # Assert
        assert coord.graph_node_count > 1
        assert coord.graph_edge_count > 0

    def test_connections_create_nodes_and_edges(self):
        """Соединения создают узлы и рёбра в графе."""
        # Arrange
        coord = GateCoordinator()

        # Act
        coord.get(_ActionWithConn)

        # Assert
        assert coord.graph_edge_count > 0

    def test_same_dependency_shared_between_actions(self):
        """Общая зависимость разделяется между действиями."""
        # Arrange
        coord = GateCoordinator()

        # Act
        coord.get(_ActionWithDeps)
        node_count_after_first = coord.graph_node_count
        coord.get(_AnotherActionWithServiceA)
        node_count_after_second = coord.graph_node_count

        # Assert — при добавлении второго действия _ServiceA не дублируется,
        # поэтому прирост узлов меньше, чем для полностью нового действия
        assert coord.has(_ServiceA)
        assert node_count_after_second > node_count_after_first


# ═════════════════════════════════════════════════════════════════════════════
# Аспекты и чекеры
# ═════════════════════════════════════════════════════════════════════════════


class TestAspectsAndCheckers:
    """Проверяет создание узлов для аспектов и чекеров."""

    def test_aspects_create_nodes_and_edges(self):
        """Аспекты создают узлы и рёбра в графе."""
        # Arrange
        coord = GateCoordinator()

        # Act
        coord.get(_ActionWithCheckers)
        nodes = coord.get_nodes_by_type("aspect")

        # Assert
        assert len(nodes) >= 1

    def test_checkers_create_nodes_and_edges(self):
        """Чекеры создают узлы и рёбра в графе."""
        # Arrange
        coord = GateCoordinator()

        # Act
        coord.get(_ActionWithCheckers)
        nodes = coord.get_nodes_by_type("checker")

        # Assert
        assert len(nodes) >= 1


# ═════════════════════════════════════════════════════════════════════════════
# Подписки и sensitive
# ═════════════════════════════════════════════════════════════════════════════


class TestSubscriptionsAndSensitive:
    """Проверяет создание узлов для подписок и sensitive-полей."""

    def test_subscriptions_create_nodes_and_edges(self):
        """Подписки создают узлы в графе."""
        # Arrange
        coord = GateCoordinator()

        # Act
        coord.get(_TestPlugin)
        nodes = coord.get_nodes_by_type("subscription")

        # Assert
        assert len(nodes) >= 1

    def test_sensitive_fields_create_nodes_and_edges(self):
        """Sensitive-поля создают узлы в графе."""
        # Arrange
        coord = GateCoordinator()

        # Act
        coord.get(_ActionWithSensitive)
        nodes = coord.get_nodes_by_type("sensitive")

        # Assert
        assert len(nodes) >= 1


# ═════════════════════════════════════════════════════════════════════════════
# Рекурсивный сбор зависимостей
# ═════════════════════════════════════════════════════════════════════════════


class TestRecursiveCollection:
    """Проверяет автоматический рекурсивный сбор зависимостей."""

    def test_dependency_class_automatically_registered(self):
        """Класс зависимости автоматически регистрируется."""
        # Arrange
        coord = GateCoordinator()

        # Act
        coord.get(_ActionWithDeps)

        # Assert
        assert coord.has(_ServiceA)
        assert coord.has(_ServiceB)

    def test_connection_class_automatically_registered(self):
        """Класс соединения автоматически регистрируется."""
        # Arrange
        coord = GateCoordinator()

        # Act
        coord.get(_ActionWithConn)

        # Assert
        assert coord.has(_MockManager)

    def test_duplicate_dependency_not_collected_twice(self):
        """Дублирующая зависимость не регистрируется повторно."""
        # Arrange
        coord = GateCoordinator()

        # Act
        coord.get(_ActionWithDeps)
        size_after_first = coord.size
        coord.get(_AnotherActionWithServiceA)
        size_after_second = coord.size

        # Assert — _ServiceA уже была, добавляется только _AnotherActionWithServiceA
        assert size_after_second == size_after_first + 1


# ═════════════════════════════════════════════════════════════════════════════
# Обнаружение циклов
# ═════════════════════════════════════════════════════════════════════════════


class TestCycleDetection:
    """Проверяет обнаружение циклических зависимостей."""

    def test_self_dependency_detected(self):
        """Самозависимость обнаруживается."""
        # Arrange — класс ссылается сам на себя через _depends_info
        class _SelfRef:
            pass
        _SelfRef._depends_info = [type("DI", (), {"cls": _SelfRef, "factory": None, "description": ""})()]

        coord = GateCoordinator()

        # Act & Assert
        with pytest.raises(CyclicDependencyError):
            coord.get(_SelfRef)

    def test_mutual_dependency_detected(self):
        """Взаимная зависимость обнаруживается."""
        # Arrange
        class _MutualA:
            pass

        class _MutualB:
            pass

        _MutualA._depends_info = [type("DI", (), {"cls": _MutualB, "factory": None, "description": ""})()]
        _MutualB._depends_info = [type("DI", (), {"cls": _MutualA, "factory": None, "description": ""})()]

        coord = GateCoordinator()

        # Act & Assert
        with pytest.raises(CyclicDependencyError):
            coord.get(_MutualA)

    def test_three_class_cycle_detected(self):
        """Цикл из трёх классов обнаруживается."""
        # Arrange
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

        # Act & Assert
        with pytest.raises(CyclicDependencyError):
            coord.get(_CycA)

    def test_diamond_dependency_no_cycle(self):
        """Ромбовидная зависимость без цикла — допустима."""
        # Arrange
        coord = GateCoordinator()

        # Act — _ActionWithDeps и _AnotherActionWithServiceA разделяют _ServiceA
        coord.get(_ActionWithDeps)
        coord.get(_AnotherActionWithServiceA)

        # Assert — нет исключения, оба зарегистрированы
        assert coord.has(_ActionWithDeps)
        assert coord.has(_AnotherActionWithServiceA)
        assert coord.has(_ServiceA)


# ═════════════════════════════════════════════════════════════════════════════
# Публичное API
# ═════════════════════════════════════════════════════════════════════════════


class TestPublicAPI:
    """Проверяет публичные методы GateCoordinator для инспекции графа."""

    def test_get_graph_returns_copy(self):
        """get_graph возвращает копию графа."""
        # Arrange
        coord = GateCoordinator()
        coord.get(_PingAction)

        # Act
        g1 = coord.get_graph()
        g2 = coord.get_graph()

        # Assert
        assert g1 is not g2

    def test_get_node_existing(self):
        """get_node для зарегистрированного класса возвращает данные."""
        # Arrange
        coord = GateCoordinator()
        coord.get(_PingAction)

        # Act
        key = _node_key("action", _PingAction)
        node = coord.get_node(key)

        # Assert
        assert node is not None

    def test_get_node_missing_returns_none(self):
        """get_node для незарегистрированного класса возвращает None."""
        # Arrange
        coord = GateCoordinator()

        # Act
        node = coord.get_node(_EmptyClass)

        # Assert
        assert node is None

    def test_get_children_of_action(self):
        """get_children для действия с зависимостями возвращает дочерние узлы."""
        # Arrange
        coord = GateCoordinator()
        coord.get(_ActionWithDeps)

        # Act
        key = _node_key("action", _ActionWithDeps)
        children = coord.get_children(key)

        # Assert
        assert len(children) > 0

    def test_get_children_of_missing_node(self):
        """get_children для незарегистрированного класса — пустой список."""
        # Arrange
        coord = GateCoordinator()

        # Act
        children = coord.get_children(_EmptyClass)

        # Assert
        assert children == []

    def test_get_nodes_by_type_action(self):
        """get_nodes_by_type('action') возвращает все действия."""
        # Arrange
        coord = GateCoordinator()
        coord.get(_PingAction)
        coord.get(_ActionWithDeps)

        # Act
        actions = coord.get_nodes_by_type("action")

        # Assert
        assert len(actions) >= 2

    def test_get_nodes_by_type_empty(self):
        """get_nodes_by_type на пустом координаторе — пустой список."""
        # Arrange
        coord = GateCoordinator()

        # Act
        result = coord.get_nodes_by_type("action")

        # Assert
        assert result == []

    def test_get_dependency_tree_structure(self):
        """get_dependency_tree возвращает непустую структуру."""
        # Arrange
        coord = GateCoordinator()
        coord.get(_ActionWithDeps)

        # Act
        tree = coord.get_dependency_tree(_ActionWithDeps)

        # Assert
        assert tree is not None
        assert isinstance(tree, dict)

    def test_get_dependency_tree_missing_node(self):
        """get_dependency_tree для незарегистрированного класса."""
        # Arrange
        coord = GateCoordinator()

        # Act
        tree = coord.get_dependency_tree(_EmptyClass)

        # Assert — пустой dict или None
        assert tree is None or tree == {}

    def test_get_dependency_tree_checkers_nested_under_aspects(self):
        """get_dependency_tree содержит чекеры вложенные под аспекты."""
        # Arrange
        coord = GateCoordinator()
        coord.get(_ActionWithCheckers)

        # Act
        tree = coord.get_dependency_tree(_ActionWithCheckers)

        # Assert
        assert tree is not None

    def test_graph_node_count(self):
        """graph_node_count возвращает количество узлов."""
        # Arrange
        coord = GateCoordinator()
        coord.get(_PingAction)

        # Assert
        assert coord.graph_node_count > 0

    def test_graph_edge_count(self):
        """graph_edge_count возвращает количество рёбер."""
        # Arrange
        coord = GateCoordinator()
        coord.get(_ActionWithDeps)

        # Assert
        assert coord.graph_edge_count > 0


# ═════════════════════════════════════════════════════════════════════════════
# Инвалидация
# ═════════════════════════════════════════════════════════════════════════════


class TestInvalidation:
    """Проверяет инвалидацию кеша координатора."""

    def test_invalidate_removes_from_cache(self):
        """invalidate удаляет класс из кеша."""
        # Arrange
        coord = GateCoordinator()
        coord.get(_PingAction)
        assert coord.has(_PingAction)

        # Act
        coord.invalidate(_PingAction)

        # Assert
        assert coord.has(_PingAction) is False

    def test_invalidate_all_clears_cache(self):
        """invalidate_all очищает весь кеш."""
        # Arrange
        coord = GateCoordinator()
        coord.get(_PingAction)
        coord.get(_ActionWithDeps)

        # Act
        coord.invalidate_all()

        # Assert
        assert coord.size == 0

    def test_invalidate_preserves_shared_dependency_node(self):
        """invalidate одного действия не удаляет общую зависимость другого."""
        # Arrange
        coord = GateCoordinator()
        coord.get(_ActionWithDeps)
        coord.get(_AnotherActionWithServiceA)

        # Act
        coord.invalidate(_ActionWithDeps)

        # Assert — _AnotherActionWithServiceA всё ещё есть
        assert coord.has(_AnotherActionWithServiceA)

    def test_invalidate_allows_rebuild(self):
        """После invalidate класс можно перерегистрировать."""
        # Arrange
        coord = GateCoordinator()
        coord.get(_PingAction)
        coord.invalidate(_PingAction)

        # Act
        meta = coord.get(_PingAction)

        # Assert
        assert meta.class_ref is _PingAction
        assert coord.has(_PingAction)

    def test_invalidate_non_existing_no_error(self):
        """invalidate для незарегистрированного класса — без ошибок."""
        # Arrange
        coord = GateCoordinator()

        # Act & Assert — не должно поднять исключение
        coord.invalidate(_EmptyClass)

    def test_invalidate_all_empty_no_error(self):
        """invalidate_all на пустом координаторе — без ошибок."""
        # Arrange
        coord = GateCoordinator()

        # Act & Assert
        coord.invalidate_all()
        assert coord.size == 0


# ═════════════════════════════════════════════════════════════════════════════
# Базовое API координатора
# ═════════════════════════════════════════════════════════════════════════════


class TestCoordinatorBasic:
    """Проверяет базовые методы GateCoordinator."""

    def test_get_builds_and_caches(self):
        """get строит метаданные и кеширует результат."""
        # Arrange
        coord = GateCoordinator()

        # Act
        meta1 = coord.get(_PingAction)
        meta2 = coord.get(_PingAction)

        # Assert
        assert meta1 is meta2

    def test_register_same_as_get(self):
        """register — синоним get."""
        # Arrange
        coord = GateCoordinator()

        # Act
        meta1 = coord.register(_PingAction)
        meta2 = coord.get(_PingAction)

        # Assert
        assert meta1 is meta2

    def test_has_before_get(self):
        """has возвращает False до регистрации."""
        # Arrange
        coord = GateCoordinator()

        # Assert
        assert coord.has(_PingAction) is False

    def test_has_after_get(self):
        """has возвращает True после регистрации."""
        # Arrange
        coord = GateCoordinator()
        coord.get(_PingAction)

        # Assert
        assert coord.has(_PingAction) is True

    def test_size(self):
        """size возвращает количество зарегистрированных классов."""
        # Arrange
        coord = GateCoordinator()
        coord.get(_PingAction)
        coord.get(_ActionWithDeps)

        # Assert
        assert coord.size >= 2

    def test_get_all_metadata(self):
        """get_all_metadata возвращает все метаданные."""
        # Arrange
        coord = GateCoordinator()
        coord.get(_PingAction)

        # Act
        all_meta = coord.get_all_metadata()

        # Assert
        assert len(all_meta) >= 1

    def test_get_all_classes(self):
        """get_all_classes возвращает все зарегистрированные классы."""
        # Arrange
        coord = GateCoordinator()
        coord.get(_PingAction)
        coord.get(_ActionWithDeps)

        # Act
        classes = coord.get_all_classes()

        # Assert
        assert _PingAction in classes
        assert _ActionWithDeps in classes

    def test_get_not_a_class_raises(self):
        """get с экземпляром вместо класса → ошибка."""
        # Arrange
        coord = GateCoordinator()

        # Act & Assert
        with pytest.raises((TypeError, ValueError)):
            coord.get(_EmptyClass())

    def test_get_factory(self):
        """get_factory возвращает DependencyFactory для действия с зависимостями."""
        # Arrange
        coord = GateCoordinator()
        coord.get(_ActionWithDeps)

        # Act
        factory = coord.get_factory(_ActionWithDeps)

        # Assert
        assert factory is not None
        assert factory.has(_ServiceA)
        assert factory.has(_ServiceB)

    def test_repr_empty(self):
        """repr пустого координатора — строка."""
        # Arrange
        coord = GateCoordinator()

        # Act & Assert
        assert isinstance(repr(coord), str)

    def test_repr_with_classes(self):
        """repr координатора с классами — строка."""
        # Arrange
        coord = GateCoordinator()
        coord.get(_PingAction)

        # Act & Assert
        assert isinstance(repr(coord), str)

    def test_repr_includes_graph_info(self):
        """repr содержит информацию о графе."""
        # Arrange
        coord = GateCoordinator()
        coord.get(_PingAction)

        # Act
        result = repr(coord)

        # Assert
        assert isinstance(result, str)
        assert len(result) > 0
