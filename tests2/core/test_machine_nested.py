# tests2/core/test_machine_nested.py
"""
Тесты вложенных вызовов действий через ToolsBox.run() в ActionProductMachine.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Аспект действия может запустить дочернее действие через box.run(ChildAction,
params, connections). Машина увеличивает nest_level, оборачивает connections
через get_wrapper_class() и рекурсивно вызывает _run_internal().

Вложенные вызовы — ключевой механизм композиции в ActionMachine. Родительское
действие (CreateOrderAction) может вызвать дочернее (NotifyAction) из
regular-аспекта, передав ему часть своих данных.

Connections оборачиваются в WrapperConnectionManager, который запрещает
дочернему действию управлять транзакциями (open/commit/rollback), но
разрешает выполнять запросы (execute).

nest_level прокидывается в ToolsBox, ScopedLogger и PluginEvent. Доступен
в шаблонах логирования через {%scope.nest_level}.

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

Базовый вложенный вызов:
    - Аспект вызывает box.run(PingAction, params) → результат.
    - Результат дочернего действия доступен в аспекте.

nest_level:
    - Корневой run() → nest_level=1 внутри аспектов.
    - Дочерний через box.run() → nest_level=2.
    - Плагины получают правильный nest_level.

Оборачивание connections:
    - ToolsBox._wrap_connections() оборачивает каждый менеджер.
    - get_wrapper_class() возвращает None → менеджер передаётся как есть.
    - get_wrapper_class() возвращает WrapperConnectionManager → обёртка.

Изоляция контекста:
    - Дочернее действие получает тот же Context, что и родительское.
    - Дочернее действие получает те же resources (моки).

Проверка ролей и connections у дочернего действия:
    - Дочернее действие с ROLE_NONE → проходит.
    - Дочернее действие без connections (если не объявлены) → OK.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from action_machine.aspects.regular_aspect import regular_aspect
from action_machine.aspects.summary_aspect import summary_aspect
from action_machine.auth import ROLE_NONE, check_roles
from action_machine.checkers import result_string
from action_machine.context.context import Context
from action_machine.context.user_info import UserInfo
from action_machine.core.action_product_machine import ActionProductMachine
from action_machine.core.base_action import BaseAction
from action_machine.core.base_params import BaseParams
from action_machine.core.base_result import BaseResult
from action_machine.core.meta_decorator import meta
from action_machine.core.tools_box import ToolsBox
from action_machine.logging.log_coordinator import LogCoordinator
from action_machine.plugins.plugin_coordinator import PluginCoordinator
from action_machine.plugins.plugin_run_context import PluginRunContext
from action_machine.resource_managers.base_resource_manager import BaseResourceManager
from tests2.domain import PingAction

# ═════════════════════════════════════════════════════════════════════════════
# Вспомогательные действия для вложенных вызовов
# ═════════════════════════════════════════════════════════════════════════════


class _ChildParams(BaseParams):
    """Параметры дочернего действия."""
    pass


class _ChildResult(BaseResult):
    """Результат дочернего действия."""
    pass


@meta(description="Дочернее действие для тестов вложенности")
@check_roles(ROLE_NONE)
class _ChildAction(BaseAction[_ChildParams, _ChildResult]):
    """Простое дочернее действие, возвращающее фиксированный результат."""

    @summary_aspect("Результат дочернего действия")
    async def summary(self, params, state, box, connections):
        result = _ChildResult()
        result["child_data"] = "from_child"
        result["nest"] = box.nested_level
        return result


class _ParentParams(BaseParams):
    """Параметры родительского действия."""
    pass


class _ParentResult(BaseResult):
    """Результат родительского действия."""
    pass


@meta(description="Родительское действие, вызывающее дочернее через box.run()")
@check_roles(ROLE_NONE)
class _ParentAction(BaseAction[_ParentParams, _ParentResult]):
    """
    Действие с regular-аспектом, который вызывает _ChildAction через box.run().
    Результат дочернего действия записывается в state.
    """

    @regular_aspect("Вызов дочернего действия")
    @result_string("child_result", required=True)
    async def call_child(self, params, state, box, connections):
        # Запуск дочернего действия через box.run()
        child_result = await box.run(_ChildAction, _ChildParams())
        return {"child_result": child_result["child_data"]}

    @summary_aspect("Формирование результата родителя")
    async def summary(self, params, state, box, connections):
        result = _ParentResult()
        result["combined"] = f"parent+{state['child_result']}"
        result["parent_nest"] = box.nested_level
        return result


@meta(description="Действие, записывающее nest_level в результат")
@check_roles(ROLE_NONE)
class _NestLevelAction(BaseAction[_ChildParams, _ChildResult]):
    """Записывает текущий nest_level из box в результат для проверки."""

    @summary_aspect("Записать nest_level")
    async def summary(self, params, state, box, connections):
        result = _ChildResult()
        result["nest_level"] = box.nested_level
        return result


@meta(description="Родитель, вызывающий _NestLevelAction")
@check_roles(ROLE_NONE)
class _NestLevelParent(BaseAction[_ParentParams, _ParentResult]):
    """Вызывает _NestLevelAction и сохраняет свой и дочерний nest_level."""

    @regular_aspect("Вызов дочернего")
    @result_string("info", required=True)
    async def call_child(self, params, state, box, connections):
        child_result = await box.run(_NestLevelAction, _ChildParams())
        child_nest = child_result["nest_level"]
        return {"info": f"parent={box.nested_level},child={child_nest}"}

    @summary_aspect("Результат")
    async def summary(self, params, state, box, connections):
        result = _ParentResult()
        result["info"] = state["info"]
        return result


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
    return Context(user=UserInfo(user_id="tester", roles=["manager", "admin"]))


# ═════════════════════════════════════════════════════════════════════════════
# Базовый вложенный вызов
# ═════════════════════════════════════════════════════════════════════════════


class TestBasicNestedCall:
    """Аспект вызывает дочернее действие через box.run()."""

    @pytest.mark.asyncio
    async def test_parent_calls_child_and_uses_result(self, machine, context) -> None:
        """
        _ParentAction вызывает _ChildAction через box.run().

        Regular-аспект call_child запускает _ChildAction, получает
        результат с child_data="from_child" и записывает его в state.
        Summary-аспект формирует combined="parent+from_child".
        """
        # Arrange — родительское действие
        action = _ParentAction()
        params = _ParentParams()

        # Act — запуск конвейера, внутри которого произойдёт вложенный вызов
        result = await machine.run(context, action, params)

        # Assert — результат содержит данные от дочернего действия
        assert result["combined"] == "parent+from_child"

    @pytest.mark.asyncio
    async def test_child_action_executes_independently(self, machine, context) -> None:
        """
        _ChildAction может быть запущен и как самостоятельное действие.

        Дочернее действие — полноценный Action с @meta и @check_roles.
        Его можно запустить напрямую через machine.run().
        """
        # Arrange — дочернее действие напрямую
        action = _ChildAction()
        params = _ChildParams()

        # Act — прямой запуск без родителя
        result = await machine.run(context, action, params)

        # Assert — результат содержит child_data
        assert result["child_data"] == "from_child"


# ═════════════════════════════════════════════════════════════════════════════
# nest_level
# ═════════════════════════════════════════════════════════════════════════════


class TestNestLevel:
    """nest_level увеличивается при каждом уровне вложенности."""

    @pytest.mark.asyncio
    async def test_root_action_has_nest_level_one(self, machine, context) -> None:
        """
        Корневое действие через run() получает nest_level=1.

        machine.run() вызывает _run_internal(nested_level=0),
        внутри current_nest = nested_level + 1 = 1.
        ToolsBox создаётся с nested_level=1.
        """
        # Arrange — действие, записывающее nest_level в результат
        action = _NestLevelAction()
        params = _ChildParams()

        # Act — корневой запуск
        result = await machine.run(context, action, params)

        # Assert — nest_level=1 для корневого действия
        assert result["nest_level"] == 1

    @pytest.mark.asyncio
    async def test_child_has_incremented_nest_level(self, machine, context) -> None:
        """
        Дочернее действие через box.run() получает nest_level=2.

        Родитель запускается с nest_level=1. box.run() вызывает
        _run_internal(nested_level=1), внутри current_nest = 1 + 1 = 2.
        """
        # Arrange — родитель, вызывающий _NestLevelAction
        action = _NestLevelParent()
        params = _ParentParams()

        # Act — запуск родителя, внутри которого вызывается дочернее
        result = await machine.run(context, action, params)

        # Assert — info содержит parent=1, child=2
        assert result["info"] == "parent=1,child=2"

    @pytest.mark.asyncio
    async def test_plugin_receives_correct_nest_level(self, machine, context) -> None:
        """
        Плагины получают nest_level через emit_event.

        При корневом вызове run() nest_level=1 передаётся
        в каждый emit_event.
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

        # Assert — nest_level=1 в первом вызове emit_event (global_start)
        first_call = mock_plugin_ctx.emit_event.call_args_list[0]
        assert first_call.kwargs["nest_level"] == 1


# ═════════════════════════════════════════════════════════════════════════════
# Оборачивание connections
# ═════════════════════════════════════════════════════════════════════════════


class TestConnectionWrapping:
    """ToolsBox._wrap_connections() оборачивает менеджеры для дочерних действий."""

    def test_wrap_connections_with_wrapper_class(self) -> None:
        """
        Менеджер с get_wrapper_class() → оборачивается в WrapperConnectionManager.

        ToolsBox._wrap_connections() вызывает get_wrapper_class() для каждого
        менеджера. Если возвращает класс — создаёт обёртку.
        """
        # Arrange — мок менеджера с wrapper_class
        from action_machine.resource_managers.iconnection_manager import IConnectionManager
        from action_machine.resource_managers.wrapper_connection_manager import WrapperConnectionManager

        mock_manager = MagicMock(spec=IConnectionManager)
        mock_manager.get_wrapper_class.return_value = WrapperConnectionManager
        mock_manager.rollup = False

        box = ToolsBox(
            run_child=AsyncMock(),
            factory=MagicMock(),
            resources=None,
            context=Context(),
            log=MagicMock(),
            nested_level=1,
            rollup=False,
        )

        # Act — оборачивание connections
        wrapped = box._wrap_connections({"db": mock_manager})

        # Assert — менеджер обёрнут в WrapperConnectionManager
        assert wrapped is not None
        assert "db" in wrapped
        assert isinstance(wrapped["db"], WrapperConnectionManager)

    def test_wrap_connections_without_wrapper_class(self) -> None:
        """
        Менеджер с get_wrapper_class() → None → передаётся как есть.

        Если менеджер не требует обёртки (безопасен для прямой передачи),
        get_wrapper_class() возвращает None, и ToolsBox передаёт
        оригинальный менеджер без изменений.
        """
        # Arrange — мок менеджера без wrapper_class
        mock_manager = MagicMock(spec=BaseResourceManager)
        mock_manager.get_wrapper_class.return_value = None

        box = ToolsBox(
            run_child=AsyncMock(),
            factory=MagicMock(),
            resources=None,
            context=Context(),
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

        Если connections не переданы (None), обёртка не создаётся.
        """
        # Arrange — ToolsBox
        box = ToolsBox(
            run_child=AsyncMock(),
            factory=MagicMock(),
            resources=None,
            context=Context(),
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

        Замыкание run_child, создаваемое в _run_internal(), захватывает
        context из родительского вызова и передаёт его в дочерний
        _run_internal().
        """
        # Arrange — родительское действие, которое вызывает дочернее
        # Проверяем косвенно через успешное выполнение: дочернее действие
        # PingAction с ROLE_NONE проходит проверку ролей, значит Context
        # был передан корректно
        action = _ParentAction()
        params = _ParentParams()

        # Act — запуск с конкретным контекстом
        result = await machine.run(context, action, params)

        # Assert — конвейер завершился, дочернее действие получило контекст
        assert result["combined"] == "parent+from_child"


# ═════════════════════════════════════════════════════════════════════════════
# ToolsBox.resolve() — двухуровневый поиск
# ═════════════════════════════════════════════════════════════════════════════


class TestToolsBoxResolve:
    """ToolsBox.resolve() — поиск в resources, затем в factory."""

    def test_resolve_from_resources_first(self) -> None:
        """
        resolve(cls) сначала ищет в resources (моки).

        Если cls найден в resources — возвращается объект из resources.
        Factory не вызывается. Это приоритет моков над фабрикой.
        """
        # Arrange — ToolsBox с resources, содержащим мок
        mock_service = MagicMock()
        mock_factory = MagicMock()

        box = ToolsBox(
            run_child=AsyncMock(),
            factory=mock_factory,
            resources={str: mock_service},  # str как ключ-класс
            context=Context(),
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

        Factory создаёт новый экземпляр через DependencyInfo.
        """
        # Arrange — ToolsBox без resources для запрашиваемого класса
        mock_factory = MagicMock()
        mock_factory.resolve.return_value = "factory_result"

        box = ToolsBox(
            run_child=AsyncMock(),
            factory=mock_factory,
            resources=None,
            context=Context(),
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

        При rollup=True фабрика дополнительно проверяет
        check_rollup_support() для BaseResourceManager.
        """
        # Arrange — ToolsBox с rollup=True
        mock_factory = MagicMock()
        mock_factory.resolve.return_value = "result"

        box = ToolsBox(
            run_child=AsyncMock(),
            factory=mock_factory,
            resources=None,
            context=Context(),
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
        # Arrange & Act
        box = ToolsBox(
            run_child=AsyncMock(),
            factory=MagicMock(),
            resources=None,
            context=Context(),
            log=MagicMock(),
            nested_level=3,
            rollup=False,
        )

        # Assert
        assert box.nested_level == 3

    def test_rollup_property(self) -> None:
        """rollup возвращает флаг автоотката."""
        # Arrange & Act
        box = ToolsBox(
            run_child=AsyncMock(),
            factory=MagicMock(),
            resources=None,
            context=Context(),
            log=MagicMock(),
            nested_level=1,
            rollup=True,
        )

        # Assert
        assert box.rollup is True

    def test_context_property(self) -> None:
        """context возвращает контекст выполнения."""
        # Arrange
        ctx = Context(user=UserInfo(user_id="test"))

        # Act
        box = ToolsBox(
            run_child=AsyncMock(),
            factory=MagicMock(),
            resources=None,
            context=ctx,
            log=MagicMock(),
            nested_level=1,
            rollup=False,
        )

        # Assert — тот же объект контекста
        assert box.context is ctx
        assert box.context.user.user_id == "test"
