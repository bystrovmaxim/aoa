# tests/core/test_machine_nested.py
"""
Тесты вложенных вызовов действий через ToolsBox.run() в ActionProductMachine.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Аспект действия может запустить дочернее действие через box.run(ChildAction,
params, connections). Машина увеличивает nest_level, оборачивает connections
через get_wrapper_class() и рекурсивно вызывает _run_internal().

Connections оборачиваются в WrapperSqlConnectionManager, который запрещает
дочернему действию управлять транзакциями (open/commit/rollback), но
разрешает выполнять запросы (execute).

nest_level прокидывается в ToolsBox, ScopedLogger и PluginEvent. Доступен
в шаблонах логирования через {%scope.nest_level}.

Прямой доступ к контексту через box закрыт. Аспекты получают данные
контекста исключительно через ContextView при наличии @context_requires.

Все core-типы (Params, Result, State) — frozen. Аспекты не могут мутировать
state или result — только создавать новые экземпляры.

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

Базовый вложенный вызов:
    - Аспект вызывает box.run(ChildAction, params) → результат.
    - Результат дочернего действия доступен в аспекте.

nest_level:
    - Корневой run() → nest_level=1.
    - Дочерний через box.run() → nest_level=2.
    - Плагины получают правильный nest_level.

Оборачивание connections:
    - ToolsBox._wrap_connections() оборачивает каждый менеджер.
    - get_wrapper_class() → None → менеджер передаётся как есть.
    - get_wrapper_class() → WrapperSqlConnectionManager → обёртка.

Изоляция контекста:
    - Дочернее действие получает тот же Context.

ToolsBox.resolve() — двухуровневый поиск:
    - resources (моки) имеют приоритет над factory.
    - rollup прокидывается в factory.resolve().
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import Field

from action_machine.intents.aspects.regular_aspect_decorator import regular_aspect
from action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from action_machine.intents.auth import NoneRole, check_roles
from action_machine.intents.checkers import result_string
from action_machine.intents.context.context import Context
from action_machine.intents.context.user_info import UserInfo
from action_machine.intents.logging.log_coordinator import LogCoordinator
from action_machine.intents.meta.meta_decorator import meta
from action_machine.intents.plugins.plugin_coordinator import PluginCoordinator
from action_machine.intents.plugins.plugin_run_context import PluginRunContext
from action_machine.model.base_action import BaseAction
from action_machine.model.base_params import BaseParams
from action_machine.model.base_result import BaseResult
from action_machine.resources.base_resource_manager import BaseResourceManager
from action_machine.runtime.machines.action_product_machine import ActionProductMachine
from action_machine.runtime.tools_box import ToolsBox
from tests.scenarios.domain_model import PingAction
from tests.scenarios.domain_model.domains import TestDomain
from tests.scenarios.domain_model.roles import AdminRole, ManagerRole

# ═════════════════════════════════════════════════════════════════════════════
# Вспомогательные действия для вложенных вызовов
# ═════════════════════════════════════════════════════════════════════════════


class _ChildParams(BaseParams):
    """Параметры дочернего действия."""
    pass


class _ChildResult(BaseResult):
    """Результат дочернего действия — frozen, все поля задаются в конструкторе."""
    child_data: str = Field(description="Данные из дочернего действия")
    nest: int = Field(description="Уровень вложенности")


@meta(description="Дочернее действие для тестов вложенности", domain=TestDomain)
@check_roles(NoneRole)
class _ChildTestAction(BaseAction[_ChildParams, _ChildResult]):
    """
    Простое дочернее действие, возвращающее фиксированный результат.

    Результат создаётся через конструктор (frozen), а не через мутацию.
    """

    @summary_aspect("Результат дочернего действия")
    async def build_summary(self, params, state, box, connections):
        # Создаём frozen-результат через конструктор
        return _ChildResult(child_data="from_child", nest=box.nested_level)


class _ParentParams(BaseParams):
    """Параметры родительского действия."""
    pass


class _ParentResult(BaseResult):
    """Результат родительского действия — frozen."""
    combined: str = Field(description="Скомбинированный результат")
    parent_nest: int = Field(description="Уровень вложенности родителя")


@meta(description="Родительское действие, вызывающее дочернее через box.run()", domain=TestDomain)
@check_roles(NoneRole)
class _ParentTestAction(BaseAction[_ParentParams, _ParentResult]):
    """
    Действие с regular-аспектом, который вызывает _ChildTestAction через box.run().
    Результат дочернего действия записывается в state.
    """

    @regular_aspect("Вызов дочернего действия")
    @result_string("child_result", required=True)
    async def call_child_aspect(self, params, state, box, connections):
        child_result = await box.run(_ChildTestAction, _ChildParams())
        # child_result — frozen, читаем поле через dot-доступ
        return {"child_result": child_result.child_data}

    @summary_aspect("Формирование результата родителя")
    async def build_summary(self, params, state, box, connections):
        # Создаём frozen-результат через конструктор
        return _ParentResult(
            combined=f"parent+{state['child_result']}",
            parent_nest=box.nested_level,
        )


@meta(description="Действие, записывающее nest_level в результат", domain=TestDomain)
@check_roles(NoneRole)
class _NestLevelTestAction(BaseAction[_ChildParams, _ChildResult]):
    """Записывает текущий nest_level из box в результат для проверки."""

    @summary_aspect("Записать nest_level")
    async def build_summary(self, params, state, box, connections):
        return _ChildResult(child_data="", nest=box.nested_level)


@meta(description="Родитель, вызывающий _NestLevelTestAction", domain=TestDomain)
@check_roles(NoneRole)
class _NestLevelParentAction(BaseAction[_ParentParams, _ParentResult]):
    """Вызывает _NestLevelTestAction и сохраняет свой и дочерний nest_level."""

    @regular_aspect("Вызов дочернего")
    @result_string("info", required=True)
    async def call_child_aspect(self, params, state, box, connections):
        child_result = await box.run(_NestLevelTestAction, _ChildParams())
        child_nest = child_result.nest
        return {"info": f"parent={box.nested_level},child={child_nest}"}

    @summary_aspect("Результат")
    async def build_summary(self, params, state, box, connections):
        return _ParentResult(combined=state["info"], parent_nest=box.nested_level)


# ═════════════════════════════════════════════════════════════════════════════
# Фикстуры
# ═════════════════════════════════════════════════════════════════════════════


@pytest.fixture()
def machine() -> ActionProductMachine:
    """ActionProductMachine с тихим логгером."""
    return ActionProductMachine(
        mode="test",
        log_coordinator=LogCoordinator(loggers=[]),
    )


@pytest.fixture()
def context() -> Context:
    """Контекст с ролями для прохождения любых проверок."""
    return Context(user=UserInfo(user_id="tester", roles=(ManagerRole, AdminRole)))


# ═════════════════════════════════════════════════════════════════════════════
# Базовый вложенный вызов
# ═════════════════════════════════════════════════════════════════════════════


class TestBasicNestedCall:
    """Аспект вызывает дочернее действие через box.run()."""

    @pytest.mark.asyncio
    async def test_parent_calls_child_and_uses_result(self, machine, context) -> None:
        """
        _ParentTestAction вызывает _ChildTestAction через box.run().

        Regular-аспект call_child_aspect запускает _ChildTestAction, получает
        результат с child_data="from_child" и записывает его в state.
        Summary-аспект формирует combined="parent+from_child".
        """
        # Arrange — родительское действие
        action = _ParentTestAction()
        params = _ParentParams()

        # Act — запуск конвейера
        result = await machine.run(context, action, params)

        # Assert — результат содержит данные от дочернего действия
        assert result.combined == "parent+from_child"

    @pytest.mark.asyncio
    async def test_child_action_executes_independently(self, machine, context) -> None:
        """
        _ChildTestAction может быть запущен и как самостоятельное действие.

        Проверяет, что дочернее действие корректно выполняется вне родителя.
        """
        # Arrange — дочернее действие напрямую
        action = _ChildTestAction()
        params = _ChildParams()

        # Act — прямой запуск без родителя
        result = await machine.run(context, action, params)

        # Assert — результат содержит child_data
        assert result.child_data == "from_child"


# ═════════════════════════════════════════════════════════════════════════════
# nest_level
# ═════════════════════════════════════════════════════════════════════════════


class TestNestLevel:
    """nest_level увеличивается при каждом уровне вложенности."""

    @pytest.mark.asyncio
    async def test_root_action_has_nest_level_one(self, machine, context) -> None:
        """
        Корневое действие через run() получает nest_level=1.

        Проверяет, что в корневом вызове box.nested_level = 1
        (0 + 1 внутри _run_internal).
        """
        # Arrange — действие, записывающее nest_level в результат
        action = _NestLevelTestAction()
        params = _ChildParams()

        # Act — корневой запуск
        result = await machine.run(context, action, params)

        # Assert — nest_level=1 для корневого действия
        assert result.nest == 1

    @pytest.mark.asyncio
    async def test_child_has_incremented_nest_level(self, machine, context) -> None:
        """
        Дочернее действие через box.run() получает nest_level=2.

        Корневое действие имеет nest_level=1, дочернее — nest_level=2.
        """
        # Arrange — родитель, вызывающий _NestLevelTestAction
        action = _NestLevelParentAction()
        params = _ParentParams()

        # Act — запуск родителя
        result = await machine.run(context, action, params)

        # Assert — info содержит parent=1, child=2
        assert result.combined == "parent=1,child=2"

    @pytest.mark.asyncio
    async def test_plugin_receives_correct_nest_level(self, machine, context) -> None:
        """
        Плагины получают nest_level через объект события.

        Машина создаёт типизированный GlobalStartEvent с nest_level
        как полем объекта и передаёт его как первый позиционный
        аргумент в emit_event().
        """
        # Arrange — машина с замоканным PluginCoordinator
        mock_plugin_ctx = AsyncMock(spec=PluginRunContext)
        mock_coordinator = AsyncMock(spec=PluginCoordinator)
        mock_coordinator.create_run_context = AsyncMock(return_value=mock_plugin_ctx)
        machine._plugin_coordinator = mock_coordinator

        action = PingAction()
        params = PingAction.Params()

        # Act — запуск с отслеживанием emit_event
        await machine.run(context, action, params)

        # Assert — nest_level=1 в первом событии (GlobalStartEvent)
        first_call = mock_plugin_ctx.emit_event.call_args_list[0]
        event = first_call.args[0]  # первый позиционный аргумент — объект события
        assert event.nest_level == 1


# ═════════════════════════════════════════════════════════════════════════════
# Оборачивание connections
# ═════════════════════════════════════════════════════════════════════════════


class TestConnectionWrapping:
    """ToolsBox._wrap_connections() оборачивает менеджеры для дочерних действий."""

    def test_wrap_connections_with_wrapper_class(self) -> None:
        """
        Менеджер с get_wrapper_class() → оборачивается в WrapperSqlConnectionManager.
        """
        from action_machine.resources.sql_connection_manager import SqlConnectionManager
        from action_machine.resources.wrapper_sql_connection_manager import (
            WrapperSqlConnectionManager,
        )

        mock_manager = MagicMock(spec=SqlConnectionManager)
        mock_manager.get_wrapper_class.return_value = WrapperSqlConnectionManager
        mock_manager.rollup = False

        box = ToolsBox(
            run_child=AsyncMock(),
            factory=MagicMock(),
            resources=None,
            log=MagicMock(),
            nested_level=1,
            rollup=False,
        )

        # Act — оборачивание connections
        wrapped = box._wrap_connections({"db": mock_manager})

        # Assert — менеджер обёрнут в WrapperSqlConnectionManager
        assert wrapped is not None
        assert "db" in wrapped
        assert isinstance(wrapped["db"], WrapperSqlConnectionManager)

    def test_wrap_connections_without_wrapper_class(self) -> None:
        """
        Менеджер с get_wrapper_class() → None → передаётся как есть.
        """
        mock_manager = MagicMock(spec=BaseResourceManager)
        mock_manager.get_wrapper_class.return_value = None

        box = ToolsBox(
            run_child=AsyncMock(),
            factory=MagicMock(),
            resources=None,
            log=MagicMock(),
            nested_level=1,
            rollup=False,
        )

        # Act — оборачивание connections
        wrapped = box._wrap_connections({"cache": mock_manager})

        # Assert — менеджер передан как есть (тот же объект)
        assert wrapped is not None
        assert wrapped["cache"] is mock_manager

    def test_wrap_connections_none_returns_none(self) -> None:
        """
        _wrap_connections(None) → None.
        """
        box = ToolsBox(
            run_child=AsyncMock(),
            factory=MagicMock(),
            resources=None,
            log=MagicMock(),
            nested_level=1,
            rollup=False,
        )

        # Act — None на входе
        result = box._wrap_connections(None)

        # Assert — None на выходе
        assert result is None


# ═════════════════════════════════════════════════════════════════════════════
# Изоляция контекста
# ═════════════════════════════════════════════════════════════════════════════


class TestContextIsolation:
    """Дочернее действие получает тот же Context и resources."""

    @pytest.mark.asyncio
    async def test_child_receives_same_context(self, machine, context) -> None:
        """
        Дочернее действие получает тот же Context, что и родительское.
        Контекст прокидывается через замыкание run_child внутри машины.
        Прямой доступ к контексту через box закрыт — аспекты получают
        данные контекста через ContextView при наличии @context_requires.
        """
        # Arrange — родительское действие, вызывающее дочернее
        action = _ParentTestAction()
        params = _ParentParams()

        # Act — запуск с конкретным контекстом
        result = await machine.run(context, action, params)

        # Assert — конвейер завершился, дочернее действие получило контекст
        assert result.combined == "parent+from_child"


# ═════════════════════════════════════════════════════════════════════════════
# ToolsBox.resolve() — двухуровневый поиск
# ═════════════════════════════════════════════════════════════════════════════


class TestToolsBoxResolve:
    """ToolsBox.resolve() — поиск в resources, затем в factory."""

    def test_resolve_from_resources_first(self) -> None:
        """
        resolve(cls) сначала ищет в resources (моки).
        """
        mock_service = MagicMock()
        mock_factory = MagicMock()

        box = ToolsBox(
            run_child=AsyncMock(),
            factory=mock_factory,
            resources={str: mock_service},
            log=MagicMock(),
            nested_level=1,
            rollup=False,
        )

        # Act — resolve ищет в resources первым
        result = box.resolve(str)

        # Assert — вернул мок из resources, factory не вызывался
        assert result is mock_service
        mock_factory.resolve.assert_not_called()

    def test_resolve_falls_through_to_factory(self) -> None:
        """
        resolve(cls) делегирует в factory, если cls нет в resources.
        """
        mock_factory = MagicMock()
        mock_factory.resolve.return_value = "factory_result"

        box = ToolsBox(
            run_child=AsyncMock(),
            factory=mock_factory,
            resources=None,
            log=MagicMock(),
            nested_level=1,
            rollup=False,
        )

        # Act — resolve не находит в resources → делегирует в factory
        result = box.resolve(str, "arg1", key="val")

        # Assert — factory.resolve вызван с аргументами и rollup
        mock_factory.resolve.assert_called_once_with(str, "arg1", rollup=False, key="val")
        assert result == "factory_result"

    def test_resolve_passes_rollup_to_factory(self) -> None:
        """
        resolve() передаёт rollup из ToolsBox в factory.resolve().
        """
        mock_factory = MagicMock()
        mock_factory.resolve.return_value = "result"

        box = ToolsBox(
            run_child=AsyncMock(),
            factory=mock_factory,
            resources=None,
            log=MagicMock(),
            nested_level=1,
            rollup=True,
        )

        # Act — resolve с rollup=True
        box.resolve(str)

        # Assert — rollup=True передан в factory.resolve
        mock_factory.resolve.assert_called_once_with(str, rollup=True)


# ═════════════════════════════════════════════════════════════════════════════
# ToolsBox — свойства
# ═════════════════════════════════════════════════════════════════════════════


class TestToolsBoxProperties:
    """Свойства ToolsBox доступны для чтения."""

    def test_nested_level_property(self) -> None:
        """nested_level возвращает уровень вложенности."""
        box = ToolsBox(
            run_child=AsyncMock(),
            factory=MagicMock(),
            resources=None,
            log=MagicMock(),
            nested_level=3,
            rollup=False,
        )
        assert box.nested_level == 3

    def test_rollup_property(self) -> None:
        """rollup возвращает флаг автоотката."""
        box = ToolsBox(
            run_child=AsyncMock(),
            factory=MagicMock(),
            resources=None,
            log=MagicMock(),
            nested_level=1,
            rollup=True,
        )
        assert box.rollup is True

    def test_context_not_accessible(self) -> None:
        """
        Публичное свойство context удалено из ToolsBox.

        Прямой доступ к контексту через box закрыт. Аспекты получают
        данные контекста исключительно через ContextView, который
        машина создаёт при наличии @context_requires. Это реализация
        принципа минимальных привилегий.
        """
        box = ToolsBox(
            run_child=AsyncMock(),
            factory=MagicMock(),
            resources=None,
            log=MagicMock(),
            nested_level=1,
            rollup=False,
        )

        # Act / Assert — атрибут context недоступен как публичное свойство
        assert not hasattr(box, "context")
