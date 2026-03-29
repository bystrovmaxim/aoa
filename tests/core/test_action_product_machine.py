# tests/core/test_action_product_machine.py
"""
Тесты для ActionProductMachine — основной машины выполнения действий.

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

- Конструктор и параметры (mode, log_coordinator).
- Проверка ролей (_check_action_roles) через ClassMetadata.
- Проверка соединений (_check_connections) через ClassMetadata:
  проверка ключей и проверка типов значений (isinstance BaseResourceManager).
- Полный цикл выполнения run(): порядок аспектов, логирование,
  события плагинов, уровень вложенности.
- Валидация результатов аспектов чекерами (ResultStringChecker).
- Ошибки: regular-аспект вернул не dict, нет чекеров, лишние поля.
- nest_level в scope логгера: корректная передача в ScopedLogger.
- Передача log_coordinator, machine_name и mode в plugin_ctx.emit_event().

═══════════════════════════════════════════════════════════════════════════════
ПРИНЦИП НАСЛЕДОВАНИЯ АСПЕКТОВ
═══════════════════════════════════════════════════════════════════════════════

Аспекты НЕ наследуются от родительского класса. Каждый класс действия
обязан явно объявить все свои аспекты через @regular_aspect и @summary_aspect.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from action_machine.aspects.regular_aspect import regular_aspect
from action_machine.aspects.summary_aspect import summary_aspect
from action_machine.auth.check_roles import CheckRoles
from action_machine.checkers.result_string_checker import ResultStringChecker
from action_machine.context.context import Context
from action_machine.context.user_info import UserInfo
from action_machine.core.action_product_machine import ActionProductMachine
from action_machine.core.base_action import BaseAction
from action_machine.core.base_params import BaseParams
from action_machine.core.base_result import BaseResult
from action_machine.core.base_state import BaseState
from action_machine.core.exceptions import AuthorizationError, ConnectionValidationError, ValidationFieldError
from action_machine.core.tools_box import ToolsBox
from action_machine.logging.log_coordinator import LogCoordinator
from action_machine.plugins.plugin import Plugin
from action_machine.plugins.plugin_coordinator import PluginCoordinator
from action_machine.plugins.plugin_run_context import PluginRunContext
from action_machine.resource_managers.base_resource_manager import BaseResourceManager
from action_machine.resource_managers.connection import connection


# ----------------------------------------------------------------------
# Вспомогательные классы
# ----------------------------------------------------------------------
class MockParams(BaseParams):
    """Пустые параметры для тестовых действий."""
    pass


class MockResult(BaseResult):
    """Пустой результат для тестовых действий."""
    pass


class MockResourceManager(BaseResourceManager):
    """Заглушка менеджера ресурсов для тестов соединений."""
    def get_wrapper_class(self) -> None:
        return None


# ----------------------------------------------------------------------
# Действия: конфигурация аспектов
# ----------------------------------------------------------------------
@CheckRoles(CheckRoles.NONE, desc="No authentication")
class ActionWithAspects(BaseAction[MockParams, MockResult]):
    """
    Действие с несколькими аспектами для проверки порядка выполнения
    и логирования.
    """
    _test_calls: list[str] = []

    @regular_aspect("First aspect")
    @ResultStringChecker("value", "Value", required=True)
    async def aspect1(
        self,
        params: MockParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict,
    ) -> dict:
        self._test_calls.append("aspect1")
        await box.info("Aspect1 executed", value="one")
        return {"value": "one"}

    @regular_aspect("Second aspect")
    @ResultStringChecker("value", "Value", required=True)
    async def aspect2(
        self,
        params: MockParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict,
    ) -> dict:
        self._test_calls.append("aspect2")
        await box.debug("Aspect2 debug")
        return {"value": "two"}

    @summary_aspect("Main aspect")
    async def summary(
        self,
        params: MockParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict,
    ) -> MockResult:
        self._test_calls.append("summary")
        await box.warning("Summary executed")
        return MockResult()


@CheckRoles(CheckRoles.NONE, desc="No authentication")
class ParentAction(BaseAction[MockParams, MockResult]):
    """Родительское действие. Аспекты не наследуются потомками."""

    @regular_aspect("Parent")
    async def parent_aspect(
        self,
        params: MockParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict,
    ) -> dict:
        return {}

    @summary_aspect("Parent summary")
    async def summary(
        self,
        params: MockParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict,
    ) -> MockResult:
        return MockResult()


@CheckRoles(CheckRoles.NONE, desc="No authentication")
class ChildAction(ParentAction):
    """Дочернее действие. Явно объявляет ВСЕ свои аспекты."""

    @regular_aspect("Child")
    async def child_aspect(
        self,
        params: MockParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict,
    ) -> dict:
        return {}

    @summary_aspect("Child summary")
    async def summary(
        self,
        params: MockParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict,
    ) -> MockResult:
        return MockResult()


# ----------------------------------------------------------------------
# Действия: проверка ролей
# ----------------------------------------------------------------------
@CheckRoles(CheckRoles.NONE, desc="No authentication")
class ActionNone(BaseAction[MockParams, MockResult]):
    @summary_aspect("mock summary")
    async def summary(self, params, state, box, connections):
        return MockResult()


@CheckRoles(CheckRoles.ANY, desc="Any role")
class ActionAny(BaseAction[MockParams, MockResult]):
    @summary_aspect("mock summary")
    async def summary(self, params, state, box, connections):
        return MockResult()


@CheckRoles("admin", desc="Only admin")
class ActionSingleRole(BaseAction[MockParams, MockResult]):
    @summary_aspect("mock summary")
    async def summary(self, params, state, box, connections):
        return MockResult()


@CheckRoles(["admin", "manager"], desc="Admin or manager")
class ActionListRole(BaseAction[MockParams, MockResult]):
    @summary_aspect("mock summary")
    async def summary(self, params, state, box, connections):
        return MockResult()


class ActionNoDecorator(BaseAction[MockParams, MockResult]):
    @summary_aspect("mock summary")
    async def summary(self, params, state, box, connections):
        return MockResult()


# ----------------------------------------------------------------------
# Действия: проверка соединений
# ----------------------------------------------------------------------
@connection(MockResourceManager, key="db", description="Database")
@CheckRoles(CheckRoles.NONE, desc="No authentication")
class ActionWithOneConnection(BaseAction[MockParams, MockResult]):
    @summary_aspect("test")
    async def summary(self, params, state, box, connections):
        assert "db" in connections
        return MockResult()


@connection(MockResourceManager, key="db")
@connection(MockResourceManager, key="cache")
@CheckRoles(CheckRoles.NONE, desc="No authentication")
class ActionWithTwoConnections(BaseAction[MockParams, MockResult]):
    @summary_aspect("test")
    async def summary(self, params, state, box, connections):
        assert "db" in connections
        assert "cache" in connections
        return MockResult()


@CheckRoles(CheckRoles.NONE, desc="No authentication")
class ActionWithoutConnections(BaseAction[MockParams, MockResult]):
    @summary_aspect("test")
    async def summary(self, params, state, box, connections):
        assert connections == {}
        return MockResult()


# ----------------------------------------------------------------------
# Действия для TestRun (ошибки)
# ----------------------------------------------------------------------
@CheckRoles(CheckRoles.NONE, desc="")
class BadAction(BaseAction[MockParams, MockResult]):
    """regular-аспект возвращает не dict."""
    @regular_aspect("bad")
    async def bad(self, params, state, box, connections):
        return "not a dict"

    @summary_aspect("bad summary")
    async def summary(self, params, state, box, connections):
        return MockResult()


@CheckRoles(CheckRoles.NONE, desc="")
class ActionWithoutCheckers(BaseAction[MockParams, MockResult]):
    """regular-аспект без чекеров, возвращающий непустой dict."""
    @regular_aspect("no checkers")
    async def aspect_no_checkers(self, params, state, box, connections):
        return {"field": "value"}

    @summary_aspect("no checkers summary")
    async def summary(self, params, state, box, connections):
        return MockResult()


@CheckRoles(CheckRoles.NONE, desc="")
class ActionWithChecker(BaseAction[MockParams, MockResult]):
    """Аспект с чекером на одно поле, но возвращает лишнее поле."""
    @regular_aspect("with checker")
    @ResultStringChecker("field", "Test field", required=True)
    async def aspect_with_checker(self, params, state, box, connections):
        return {"field": "ok", "extra": "forbidden"}

    @summary_aspect("checker summary")
    async def summary(self, params, state, box, connections):
        return MockResult()


# ----------------------------------------------------------------------
# Фикстуры
# ----------------------------------------------------------------------
@pytest.fixture
def context_with_roles() -> Context:
    user = UserInfo(user_id="test", roles=["user", "admin"])
    return Context(user=user)


@pytest.fixture
def context_without_roles() -> Context:
    user = UserInfo(user_id="guest", roles=[])
    return Context(user=user)


@pytest.fixture
def machine() -> ActionProductMachine:
    mock_log_coordinator = AsyncMock(spec=LogCoordinator)
    return ActionProductMachine(
        mode="production",
        log_coordinator=mock_log_coordinator,
    )


@pytest.fixture
def mock_plugin() -> MagicMock:
    plugin = MagicMock(spec=Plugin)
    plugin.get_handlers.return_value = []
    return plugin


# ======================================================================
# ТЕСТЫ: Конструктор и параметры
# ======================================================================
class TestConstructor:
    def test_mode_must_be_non_empty(self):
        with pytest.raises(ValueError, match="mode must be non-empty"):
            ActionProductMachine(mode="")

    def test_default_log_coordinator_created(self):
        machine = ActionProductMachine(mode="test")
        assert machine._log_coordinator is not None


# ======================================================================
# ТЕСТЫ: Проверка ролей (_check_action_roles)
# ======================================================================
class TestCheckActionRoles:
    def test_none_role_allows_any_user(self, machine, context_without_roles):
        metadata = machine._get_metadata(ActionNone())
        machine._check_action_roles(ActionNone(), context_without_roles, metadata)

    def test_any_role_allows_user_with_roles(self, machine, context_with_roles):
        metadata = machine._get_metadata(ActionAny())
        machine._check_action_roles(ActionAny(), context_with_roles, metadata)

    def test_any_role_rejects_user_without_roles(self, machine, context_without_roles):
        metadata = machine._get_metadata(ActionAny())
        with pytest.raises(AuthorizationError, match="Authentication required"):
            machine._check_action_roles(ActionAny(), context_without_roles, metadata)

    def test_single_role_match(self, machine, context_with_roles):
        metadata = machine._get_metadata(ActionSingleRole())
        machine._check_action_roles(ActionSingleRole(), context_with_roles, metadata)

    def test_single_role_no_match(self, machine, context_with_roles):
        @CheckRoles("manager", desc="")
        class _ActionManager(BaseAction[MockParams, MockResult]):
            @summary_aspect("mock summary")
            async def summary(self, params, state, box, connections):
                return MockResult()

        action = _ActionManager()
        metadata = machine._get_metadata(action)
        with pytest.raises(AuthorizationError, match="Access denied. Required role: 'manager'"):
            machine._check_action_roles(action, context_with_roles, metadata)

    def test_list_role_intersection(self, machine, context_with_roles):
        metadata = machine._get_metadata(ActionListRole())
        machine._check_action_roles(ActionListRole(), context_with_roles, metadata)

    def test_list_role_no_intersection(self, machine, context_with_roles):
        @CheckRoles(["manager", "editor"], desc="")
        class _ActionManagerEditor(BaseAction[MockParams, MockResult]):
            @summary_aspect("mock summary")
            async def summary(self, params, state, box, connections):
                return MockResult()

        action = _ActionManagerEditor()
        metadata = machine._get_metadata(action)
        with pytest.raises(AuthorizationError, match="Access denied. Required one of the roles:"):
            machine._check_action_roles(action, context_with_roles, metadata)

    def test_action_without_role_spec_raises_type_error(self, machine, context_with_roles):
        action = ActionNoDecorator()
        metadata = machine._get_metadata(action)
        with pytest.raises(TypeError, match="does not have a @CheckRoles decorator"):
            machine._check_action_roles(action, context_with_roles, metadata)


# ======================================================================
# ТЕСТЫ: Проверка соединений (_check_connections)
# ======================================================================
class TestCheckConnections:
    def test_no_declarations_no_connections_returns_empty_dict(self, machine):
        action = ActionWithoutConnections()
        metadata = machine._get_metadata(action)
        result = machine._check_connections(action, None, metadata)
        assert result == {}

    def test_no_declarations_with_connections_raises(self, machine):
        action = ActionWithoutConnections()
        metadata = machine._get_metadata(action)
        conns = {"db": MockResourceManager()}
        with pytest.raises(ConnectionValidationError, match="does not declare any @connection"):
            machine._check_connections(action, conns, metadata)

    def test_has_declarations_no_connections_raises(self, machine):
        action = ActionWithOneConnection()
        metadata = machine._get_metadata(action)
        with pytest.raises(ConnectionValidationError, match="declares connections: .*, but no connections were passed"):
            machine._check_connections(action, None, metadata)

    def test_extra_keys_raises(self, machine):
        action = ActionWithOneConnection()
        metadata = machine._get_metadata(action)
        conns = {"db": MockResourceManager(), "extra": MockResourceManager()}
        with pytest.raises(ConnectionValidationError, match="received extra connections: {'extra'}"):
            machine._check_connections(action, conns, metadata)

    def test_missing_keys_raises(self, machine):
        action = ActionWithTwoConnections()
        metadata = machine._get_metadata(action)
        conns = {"db": MockResourceManager()}
        with pytest.raises(ConnectionValidationError, match="is missing required connections: {'cache'}"):
            machine._check_connections(action, conns, metadata)

    def test_valid_connections_passes(self, machine):
        action = ActionWithTwoConnections()
        metadata = machine._get_metadata(action)
        conns = {"db": MockResourceManager(), "cache": MockResourceManager()}
        result = machine._check_connections(action, conns, metadata)
        assert result == conns

    def test_connection_value_not_resource_manager_raises(self, machine):
        action = ActionWithOneConnection()
        metadata = machine._get_metadata(action)
        conns = {"db": "это строка, а не менеджер"}
        with pytest.raises(ConnectionValidationError, match="must be an instance of BaseResourceManager"):
            machine._check_connections(action, conns, metadata)

    def test_connection_value_none_raises(self, machine):
        action = ActionWithOneConnection()
        metadata = machine._get_metadata(action)
        conns = {"db": None}
        with pytest.raises(ConnectionValidationError, match="must be an instance of BaseResourceManager"):
            machine._check_connections(action, conns, metadata)

    def test_connection_value_int_raises(self, machine):
        action = ActionWithOneConnection()
        metadata = machine._get_metadata(action)
        conns = {"db": 42}
        with pytest.raises(ConnectionValidationError, match="must be an instance of BaseResourceManager"):
            machine._check_connections(action, conns, metadata)


# ======================================================================
# ТЕСТЫ: Полный цикл run()
# ======================================================================
class TestRun:
    @pytest.mark.anyio
    async def test_run_executes_aspects_in_order(self, machine, context_with_roles):
        ActionWithAspects._test_calls = []
        result = await machine.run(context_with_roles, ActionWithAspects(), MockParams())
        assert ActionWithAspects._test_calls == ["aspect1", "aspect2", "summary"]
        assert isinstance(result, MockResult)

    @pytest.mark.anyio
    async def test_run_aspect_returns_non_dict_raises(self, machine, context_with_roles):
        with pytest.raises(TypeError, match="must return a dict"):
            await machine.run(context_with_roles, BadAction(), MockParams())

    @pytest.mark.anyio
    async def test_run_aspect_returns_dict_without_checkers_raises(self, machine, context_with_roles):
        with pytest.raises(ValidationFieldError, match="has no checkers, but returned non-empty state:"):
            await machine.run(context_with_roles, ActionWithoutCheckers(), MockParams())

    @pytest.mark.anyio
    async def test_run_aspect_returns_extra_fields_raises(self, machine, context_with_roles):
        with pytest.raises(ValidationFieldError, match="returned extra fields"):
            await machine.run(context_with_roles, ActionWithChecker(), MockParams())

    @pytest.mark.anyio
    async def test_run_calls_plugin_events(self, machine, context_with_roles):
        """
        run() эмитирует события плагинам: global_start, before/after для
        каждого аспекта, global_finish. Для ActionWithAspects (2 regular +
        1 summary) ожидается 6 событий.
        """
        mock_plugin_ctx = AsyncMock(spec=PluginRunContext)
        mock_coordinator = AsyncMock(spec=PluginCoordinator)
        mock_coordinator.create_run_context = AsyncMock(return_value=mock_plugin_ctx)
        machine._plugin_coordinator = mock_coordinator

        ActionWithAspects._test_calls = []
        await machine.run(context_with_roles, ActionWithAspects(), MockParams())
        assert mock_plugin_ctx.emit_event.await_count == 6

    @pytest.mark.anyio
    async def test_run_passes_log_coordinator_to_plugin_events(self, machine, context_with_roles):
        """
        emit_event() получает log_coordinator, machine_name и mode
        для создания ScopedLogger обработчикам плагинов.
        """
        mock_plugin_ctx = AsyncMock(spec=PluginRunContext)
        mock_coordinator = AsyncMock(spec=PluginCoordinator)
        mock_coordinator.create_run_context = AsyncMock(return_value=mock_plugin_ctx)
        machine._plugin_coordinator = mock_coordinator

        ActionWithAspects._test_calls = []
        await machine.run(context_with_roles, ActionWithAspects(), MockParams())

        # Проверяем первый вызов emit_event (global_start)
        first_call_kwargs = mock_plugin_ctx.emit_event.call_args_list[0].kwargs
        assert "log_coordinator" in first_call_kwargs
        assert first_call_kwargs["log_coordinator"] is machine._log_coordinator
        assert first_call_kwargs["machine_name"] == "ActionProductMachine"
        assert first_call_kwargs["mode"] == "production"

    @pytest.mark.anyio
    async def test_nest_level_increments_and_decrements(self, machine, context_with_roles):
        """Уровень вложенности в ToolsBox равен 1 для корневого вызова."""
        @CheckRoles(CheckRoles.NONE, desc="")
        class CheckNestingAction(BaseAction[MockParams, MockResult]):
            @summary_aspect("test")
            async def summary(self, params, state, box, connections):
                assert box.nested_level == 1
                return MockResult()

        await machine.run(context_with_roles, CheckNestingAction(), MockParams())

    @pytest.mark.anyio
    async def test_logger_passed_to_aspects(self, machine, context_with_roles):
        ActionWithAspects._test_calls = []
        await machine.run(context_with_roles, ActionWithAspects(), MockParams())
        assert machine._log_coordinator.emit.await_count >= 3

    @pytest.mark.anyio
    async def test_logger_receives_correct_scope_with_nest_level(self, machine, context_with_roles):
        """
        Логгер получает LogScope с полями machine, mode, action, aspect
        и nest_level. nest_level доступен через {%scope.nest_level}.
        """
        machine._log_coordinator.emit = AsyncMock()
        await machine.run(context_with_roles, ActionWithAspects(), MockParams())
        call_args = machine._log_coordinator.emit.call_args_list[0]
        scope = call_args.kwargs["scope"]
        assert scope["machine"] == "ActionProductMachine"
        assert scope["mode"] == "production"
        assert scope["action"] == "tests.core.test_action_product_machine.ActionWithAspects"
        assert scope["aspect"] == "aspect1"
        assert scope["nest_level"] == 1

    @pytest.mark.anyio
    async def test_mode_passed_to_logger(self, context_with_roles):
        machine_with_mode = ActionProductMachine(
            mode="staging",
            log_coordinator=AsyncMock(spec=LogCoordinator)
        )
        machine_with_mode._log_coordinator.emit = AsyncMock()
        await machine_with_mode.run(context_with_roles, ActionWithAspects(), MockParams())
        scope = machine_with_mode._log_coordinator.emit.call_args_list[0].kwargs["scope"]
        assert scope["mode"] == "staging"

    @pytest.mark.anyio
    async def test_connection_gate_used_for_validation(self, machine, context_with_roles):
        action = ActionWithOneConnection()

        conns = {"db": MockResourceManager()}
        result = await machine.run(context_with_roles, action, MockParams(), connections=conns)
        assert isinstance(result, MockResult)

        with pytest.raises(ConnectionValidationError, match="no connections were passed"):
            await machine.run(context_with_roles, action, MockParams(), connections=None)

        with pytest.raises(ConnectionValidationError, match="received extra connections"):
            await machine.run(
                context_with_roles,
                action,
                MockParams(),
                connections={"db": MockResourceManager(), "extra": MockResourceManager()}
            )

    @pytest.mark.anyio
    async def test_child_action_uses_own_aspects(self, machine, context_with_roles):
        """
        ChildAction объявляет свои аспекты (child_aspect + summary).
        Аспекты ParentAction (parent_aspect) НЕ наследуются.
        """
        result = await machine.run(context_with_roles, ChildAction(), MockParams())
        assert isinstance(result, MockResult)

        metadata = machine._get_metadata(ChildAction())
        aspect_names = [a.method_name for a in metadata.aspects]
        assert "child_aspect" in aspect_names
        assert "summary" in aspect_names
        assert "parent_aspect" not in aspect_names
