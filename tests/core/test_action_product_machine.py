# tests/core/test_action_product_machine.py
"""
Тесты ActionProductMachine — основной машины действий.

Проверяем:
- Сбор аспектов (_collect_aspects)
- Проверку ролей (_check_action_roles)
- Проверку connections (_check_connections)
- Полный конвейер run() с учётом логирования
- Передачу параметра mode и log в аспекты
- Все аспекты обязаны принимать log (шестой параметр)
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from action_machine.Auth.check_roles import CheckRoles
from action_machine.Checkers.StringFieldChecker import StringFieldChecker
from action_machine.Context.context import Context
from action_machine.Context.user_info import UserInfo
from action_machine.Core.ActionProductMachine import ActionProductMachine
from action_machine.Core.AspectMethod import aspect, connection, summary_aspect
from action_machine.Core.BaseAction import BaseAction
from action_machine.Core.BaseParams import BaseParams
from action_machine.Core.BaseResult import BaseResult
from action_machine.Core.BaseState import BaseState
from action_machine.Core.Exceptions import AuthorizationError, ConnectionValidationError, ValidationFieldError
from action_machine.Logging.action_bound_logger import ActionBoundLogger
from action_machine.Logging.log_coordinator import LogCoordinator
from action_machine.Plugins.Plugin import Plugin
from action_machine.Plugins.PluginCoordinator import PluginCoordinator
from action_machine.ResourceManagers.BaseResourceManager import BaseResourceManager


# ----------------------------------------------------------------------
# Вспомогательные классы
# ----------------------------------------------------------------------
class MockParams(BaseParams):
    pass


class MockResult(BaseResult):
    pass


class MockAction(BaseAction[MockParams, MockResult]):
    pass


class MockResourceManager(BaseResourceManager):
    def get_wrapper_class(self) -> None:
        return None


# ----------------------------------------------------------------------
# Действия: конфигурации аспектов (ВСЕ с параметром log)
# ----------------------------------------------------------------------
@CheckRoles(CheckRoles.NONE, desc="Без аутентификации")
class ActionWithAspects(MockAction):
    """Действие с несколькими аспектами для проверки порядка и логирования."""
    _test_calls: list[str] = []

    @aspect("Первый аспект")
    @StringFieldChecker("value", "Значение", required=True)
    async def aspect1(
        self,
        params: MockParams,
        state: BaseState,
        deps: dict,
        connections: dict,
        log: ActionBoundLogger,  # добавлен log
    ) -> dict:
        self._test_calls.append("aspect1")
        await log.info("Aspect1 executed", value="one")
        return {"value": "one"}

    @aspect("Второй аспект")
    @StringFieldChecker("value", "Значение", required=True)
    async def aspect2(
        self,
        params: MockParams,
        state: BaseState,
        deps: dict,
        connections: dict,
        log: ActionBoundLogger,
    ) -> dict:
        self._test_calls.append("aspect2")
        await log.debug("Aspect2 debug")
        return {"value": "two"}

    @summary_aspect("Главный аспект")
    async def summary(
        self,
        params: MockParams,
        state: BaseState,
        deps: dict,
        connections: dict,
        log: ActionBoundLogger,
    ) -> MockResult:
        self._test_calls.append("summary")
        await log.warning("Summary executed")
        return MockResult()


@CheckRoles(CheckRoles.NONE, desc="Без аутентификации")
class ActionWithoutSummary(MockAction):
    @aspect("Обычный аспект")
    async def aspect(
        self,
        params: MockParams,
        state: BaseState,
        deps: dict,
        connections: dict,
        log: ActionBoundLogger,
    ) -> dict:
        return {}


@CheckRoles(CheckRoles.NONE, desc="Без аутентификации")
class ActionWithTwoSummaries(MockAction):
    @summary_aspect("Первый")
    async def summary1(
        self,
        params: MockParams,
        state: BaseState,
        deps: dict,
        connections: dict,
        log: ActionBoundLogger,
    ) -> MockResult:
        return MockResult()

    @summary_aspect("Второй")
    async def summary2(
        self,
        params: MockParams,
        state: BaseState,
        deps: dict,
        connections: dict,
        log: ActionBoundLogger,
    ) -> MockResult:
        return MockResult()


@CheckRoles(CheckRoles.NONE, desc="Без аутентификации")
class ParentAction(MockAction):
    @aspect("Родительский")
    async def parent_aspect(
        self,
        params: MockParams,
        state: BaseState,
        deps: dict,
        connections: dict,
        log: ActionBoundLogger,
    ) -> dict:
        return {}


@CheckRoles(CheckRoles.NONE, desc="Без аутентификации")
class ChildAction(ParentAction):
    @aspect("Дочерний")
    async def child_aspect(
        self,
        params: MockParams,
        state: BaseState,
        deps: dict,
        connections: dict,
        log: ActionBoundLogger,
    ) -> dict:
        return {}

    @summary_aspect("Summary")
    async def summary(
        self,
        params: MockParams,
        state: BaseState,
        deps: dict,
        connections: dict,
        log: ActionBoundLogger,
    ) -> MockResult:
        return MockResult()


# ----------------------------------------------------------------------
# Действия: проверка ролей
# ----------------------------------------------------------------------
@CheckRoles(CheckRoles.NONE, desc="Без аутентификации")
class ActionNone(MockAction):
    @summary_aspect("test")
    async def summary(
        self,
        params: MockParams,
        state: BaseState,
        deps: dict,
        connections: dict,
        log: ActionBoundLogger,
    ) -> MockResult:
        return MockResult()


@CheckRoles(CheckRoles.ANY, desc="Любая роль")
class ActionAny(MockAction):
    @summary_aspect("test")
    async def summary(
        self,
        params: MockParams,
        state: BaseState,
        deps: dict,
        connections: dict,
        log: ActionBoundLogger,
    ) -> MockResult:
        return MockResult()


@CheckRoles("admin", desc="Только админ")
class ActionSingleRole(MockAction):
    @summary_aspect("test")
    async def summary(
        self,
        params: MockParams,
        state: BaseState,
        deps: dict,
        connections: dict,
        log: ActionBoundLogger,
    ) -> MockResult:
        return MockResult()


@CheckRoles(["admin", "manager"], desc="Админ или менеджер")
class ActionListRole(MockAction):
    @summary_aspect("test")
    async def summary(
        self,
        params: MockParams,
        state: BaseState,
        deps: dict,
        connections: dict,
        log: ActionBoundLogger,
    ) -> MockResult:
        return MockResult()


class ActionNoDecorator(MockAction):
    @summary_aspect("test")
    async def summary(
        self,
        params: MockParams,
        state: BaseState,
        deps: dict,
        connections: dict,
        log: ActionBoundLogger,
    ) -> MockResult:
        return MockResult()


# ----------------------------------------------------------------------
# Действия: проверка connections
# ----------------------------------------------------------------------
@connection("db", MockResourceManager, description="База данных")
@CheckRoles(CheckRoles.NONE, desc="Без аутентификации")
class ActionWithOneConnection(MockAction):
    @summary_aspect("test")
    async def summary(
        self,
        params: MockParams,
        state: BaseState,
        deps: dict,
        connections: dict,
        log: ActionBoundLogger,
    ) -> MockResult:
        assert "db" in connections
        return MockResult()


@connection("db", MockResourceManager)
@connection("cache", MockResourceManager)
@CheckRoles(CheckRoles.NONE, desc="Без аутентификации")
class ActionWithTwoConnections(MockAction):
    @summary_aspect("test")
    async def summary(
        self,
        params: MockParams,
        state: BaseState,
        deps: dict,
        connections: dict,
        log: ActionBoundLogger,
    ) -> MockResult:
        assert "db" in connections
        assert "cache" in connections
        return MockResult()


@CheckRoles(CheckRoles.NONE, desc="Без аутентификации")
class ActionWithoutConnections(MockAction):
    @summary_aspect("test")
    async def summary(
        self,
        params: MockParams,
        state: BaseState,
        deps: dict,
        connections: dict,
        log: ActionBoundLogger,
    ) -> MockResult:
        assert connections == {}
        return MockResult()


# ----------------------------------------------------------------------
# Действия для TestRun (ошибки и т.д.)
# ----------------------------------------------------------------------
@CheckRoles(CheckRoles.NONE, desc="")
class BadAction(MockAction):
    """Аспект возвращает не dict."""

    @aspect("bad")
    async def bad(
        self,
        params: MockParams,
        state: BaseState,
        deps: dict,
        connections: dict,
        log: ActionBoundLogger,
    ) -> str:
        return "not a dict"

    @summary_aspect("summary")
    async def summary(
        self,
        params: MockParams,
        state: BaseState,
        deps: dict,
        connections: dict,
        log: ActionBoundLogger,
    ) -> MockResult:
        return MockResult()


@CheckRoles(CheckRoles.NONE, desc="")
class ActionWithoutCheckers(MockAction):
    """Аспект возвращает непустой dict без чекеров."""

    @aspect("no checkers")
    async def aspect_no_checkers(
        self,
        params: MockParams,
        state: BaseState,
        deps: dict,
        connections: dict,
        log: ActionBoundLogger,
    ) -> dict:
        return {"field": "value"}

    @summary_aspect("summary")
    async def summary(
        self,
        params: MockParams,
        state: BaseState,
        deps: dict,
        connections: dict,
        log: ActionBoundLogger,
    ) -> MockResult:
        return MockResult()


@CheckRoles(CheckRoles.NONE, desc="")
class ActionWithChecker(MockAction):
    """Аспект возвращает лишние поля."""

    @aspect("with checker")
    @StringFieldChecker("field", "Тестовое поле", required=True)
    async def aspect_with_checker(
        self,
        params: MockParams,
        state: BaseState,
        deps: dict,
        connections: dict,
        log: ActionBoundLogger,
    ) -> dict:
        return {"field": "ok", "extra": "forbidden"}

    @summary_aspect("summary")
    async def summary(
        self,
        params: MockParams,
        state: BaseState,
        deps: dict,
        connections: dict,
        log: ActionBoundLogger,
    ) -> MockResult:
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
def machine(context_with_roles: Context) -> ActionProductMachine:
    """Машина с режимом 'production' и мок-координатором логов для проверки вызовов."""
    mock_log_coordinator = AsyncMock(spec=LogCoordinator)
    return ActionProductMachine(
        context=context_with_roles,
        mode="production",
        log_coordinator=mock_log_coordinator,
    )


@pytest.fixture
def machine_without_roles(context_without_roles: Context) -> ActionProductMachine:
    mock_log_coordinator = AsyncMock(spec=LogCoordinator)
    return ActionProductMachine(
        context=context_without_roles,
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
    def test_mode_must_be_non_empty(self, context_with_roles):
        """mode не может быть пустой строкой."""
        with pytest.raises(ValueError, match="mode must be non-empty"):
            ActionProductMachine(context_with_roles, mode="")

    def test_default_log_coordinator_created(self, context_with_roles):
        """Если log_coordinator не передан, создаётся с ConsoleLogger."""
        machine = ActionProductMachine(context_with_roles, mode="test")
        assert machine._log_coordinator is not None
        # Не можем проверить тип логера внутри, но проверим что это LogCoordinator
        from action_machine.Logging.log_coordinator import LogCoordinator
        assert isinstance(machine._log_coordinator, LogCoordinator)


# ======================================================================
# ТЕСТЫ: Сбор аспектов (_collect_aspects)
# ======================================================================
class TestCollectAspects:
    def test_collect_aspects_returns_sorted_regular_and_summary(self, context_with_roles):
        machine = ActionProductMachine(context_with_roles, mode="test")
        aspects, summary = machine._collect_aspects(ActionWithAspects)
        assert len(aspects) == 2
        assert aspects[0][0].__name__ == "aspect1"
        assert aspects[1][0].__name__ == "aspect2"
        assert aspects[0][1] == "Первый аспект"
        assert aspects[1][1] == "Второй аспект"
        assert summary.__name__ == "summary"

    def test_collect_aspects_ignores_inherited_methods(self, context_with_roles):
        machine = ActionProductMachine(context_with_roles, mode="test")
        aspects, summary = machine._collect_aspects(ChildAction)
        assert len(aspects) == 1
        assert aspects[0][0].__name__ == "child_aspect"
        assert summary.__name__ == "summary"

    def test_collect_aspects_no_summary_raises(self, context_with_roles):
        machine = ActionProductMachine(context_with_roles, mode="test")
        with pytest.raises(TypeError, match="не имеет summary_aspect"):
            machine._collect_aspects(ActionWithoutSummary)

    def test_collect_aspects_two_summaries_raises(self, context_with_roles):
        machine = ActionProductMachine(context_with_roles, mode="test")
        with pytest.raises(TypeError, match="более одного summary_aspect"):
            machine._collect_aspects(ActionWithTwoSummaries)


# ======================================================================
# ТЕСТЫ: Проверка ролей (_check_action_roles)
# ======================================================================
class TestCheckActionRoles:
    def test_none_role_allows_any_user(self, machine_without_roles):
        machine_without_roles._check_action_roles(ActionNone())

    def test_any_role_allows_user_with_roles(self, machine):
        machine._check_action_roles(ActionAny())

    def test_any_role_rejects_user_without_roles(self, machine_without_roles):
        with pytest.raises(AuthorizationError, match="Требуется аутентификация"):
            machine_without_roles._check_action_roles(ActionAny())

    def test_single_role_match(self, machine):
        machine._check_action_roles(ActionSingleRole())

    def test_single_role_no_match(self, machine):
        @CheckRoles("manager", desc="")
        class _ActionManager(MockAction):
            @summary_aspect("test")
            async def summary(
                self,
                params: MockParams,
                state: BaseState,
                deps: dict,
                connections: dict,
                log: ActionBoundLogger,
            ) -> MockResult:
                return MockResult()

        with pytest.raises(AuthorizationError, match="Требуется роль: 'manager'"):
            machine._check_action_roles(_ActionManager())

    def test_list_role_intersection(self, machine):
        machine._check_action_roles(ActionListRole())

    def test_list_role_no_intersection(self, machine):
        @CheckRoles(["manager", "editor"], desc="")
        class _ActionManagerEditor(MockAction):
            @summary_aspect("test")
            async def summary(
                self,
                params: MockParams,
                state: BaseState,
                deps: dict,
                connections: dict,
                log: ActionBoundLogger,
            ) -> MockResult:
                return MockResult()

        with pytest.raises(AuthorizationError, match="Требуется одна из ролей"):
            machine._check_action_roles(_ActionManagerEditor())

    def test_action_without_role_spec_raises_type_error(self, machine):
        with pytest.raises(TypeError, match="не имеет декоратора CheckRoles"):
            machine._check_action_roles(ActionNoDecorator())


# ======================================================================
# ТЕСТЫ: Проверка connections (_check_connections)
# ======================================================================
class TestCheckConnections:
    def test_no_declarations_no_connections_returns_empty_dict(self, machine):
        result = machine._check_connections(ActionWithoutConnections(), None)
        assert result == {}

    def test_no_declarations_with_connections_raises(self, machine):
        conns = {"db": MockResourceManager()}
        with pytest.raises(ConnectionValidationError, match="не объявляет @connection, но получило"):
            machine._check_connections(ActionWithoutConnections(), conns)

    def test_has_declarations_no_connections_raises(self, machine):
        with pytest.raises(ConnectionValidationError, match="но connections не переданы"):
            machine._check_connections(ActionWithOneConnection(), None)

    def test_extra_keys_raises(self, machine):
        conns = {"db": MockResourceManager(), "extra": MockResourceManager()}
        with pytest.raises(ConnectionValidationError, match="лишние connections"):
            machine._check_connections(ActionWithOneConnection(), conns)

    def test_missing_keys_raises(self, machine):
        conns = {"db": MockResourceManager()}
        with pytest.raises(ConnectionValidationError, match="не получило connections"):
            machine._check_connections(ActionWithTwoConnections(), conns)

    def test_valid_connections_passes(self, machine):
        conns = {"db": MockResourceManager(), "cache": MockResourceManager()}
        result = machine._check_connections(ActionWithTwoConnections(), conns)
        assert result == conns


# ======================================================================
# ТЕСТЫ: Полный конвейер run()
# ======================================================================
class TestRun:
    @pytest.mark.anyio
    async def test_run_executes_aspects_in_order(self, machine):
        ActionWithAspects._test_calls = []
        result = await machine.run(ActionWithAspects(), MockParams())
        assert ActionWithAspects._test_calls == ["aspect1", "aspect2", "summary"]
        assert isinstance(result, MockResult)

    @pytest.mark.anyio
    async def test_run_aspect_returns_non_dict_raises(self, machine):
        with pytest.raises(TypeError, match="должен возвращать dict"):
            await machine.run(BadAction(), MockParams())

    @pytest.mark.anyio
    async def test_run_aspect_returns_dict_without_checkers_raises(self, machine):
        with pytest.raises(ValidationFieldError, match="не имеет чекеров, но вернул непустой state"):
            await machine.run(ActionWithoutCheckers(), MockParams())

    @pytest.mark.anyio
    async def test_run_aspect_returns_extra_fields_raises(self, machine):
        with pytest.raises(ValidationFieldError, match="лишние поля"):
            await machine.run(ActionWithChecker(), MockParams())

    @pytest.mark.anyio
    async def test_run_calls_plugin_events(self, machine, mock_plugin):
        # Подменяем координатор плагинов моком
        machine._plugin_coordinator = AsyncMock(spec=PluginCoordinator)
        ActionWithAspects._test_calls = []
        await machine.run(ActionWithAspects(), MockParams())
        # global_start, before:aspect1, after:aspect1, before:aspect2, after:aspect2, global_finish
        assert machine._plugin_coordinator.emit_event.await_count == 6

    @pytest.mark.anyio
    async def test_nest_level_increments_and_decrements(self, machine):
        assert machine._nest_level == 0
        ActionWithAspects._test_calls = []
        await machine.run(ActionWithAspects(), MockParams())
        assert machine._nest_level == 0

    # ------------------------------------------------------------------
    # ТЕСТЫ: Проверка передачи log и вызовов координатора логов
    # ------------------------------------------------------------------
    @pytest.mark.anyio
    async def test_logger_passed_to_aspects(self, machine):
        """Проверяем, что в каждом аспекте log вызывает emit."""
        # У machine уже мок-координатор
        ActionWithAspects._test_calls = []
        await machine.run(ActionWithAspects(), MockParams())

        # Координатор логов должен был получить вызовы от каждого аспекта
        # aspect1: log.info, aspect2: log.debug, summary: log.warning
        assert machine._log_coordinator.emit.await_count >= 3

    @pytest.mark.anyio
    async def test_logger_receives_correct_scope(self, machine):
        """Проверяем, что в логере скоуп сформирован правильно."""
        # Перехватываем вызовы emit
        machine._log_coordinator.emit = AsyncMock()

        await machine.run(ActionWithAspects(), MockParams())

        # Берём первый вызов (от aspect1)
        call_args = machine._log_coordinator.emit.call_args_list[0]
        scope = call_args.kwargs["scope"]
        assert scope["machine"] == "ActionProductMachine"
        assert scope["mode"] == "production"
        assert scope["action"] == "tests.core.test_action_product_machine.ActionWithAspects"
        assert scope["aspect"] == "aspect1"
        # Проверяем порядок ключей
        assert list(scope.keys()) == ["machine", "mode", "action", "aspect"]

    @pytest.mark.anyio
    async def test_logger_receives_correct_indent(self, machine):
        """Проверяем, что уровень вложенности передаётся в логер."""
        machine._log_coordinator.emit = AsyncMock()

        # Запускаем действие (nest_level станет 1 внутри)
        await machine.run(ActionWithAspects(), MockParams())

        for call in machine._log_coordinator.emit.call_args_list:
            indent = call.kwargs["indent"]
            assert indent == 1  # внутри run nest_level=1

    @pytest.mark.anyio
    async def test_logger_passed_empty_state_and_params(self, machine):
        """Проверяем, что в логер передаются пустые BaseState и BaseParams."""
        machine._log_coordinator.emit = AsyncMock()

        await machine.run(ActionWithAspects(), MockParams())

        for call in machine._log_coordinator.emit.call_args_list:
            state = call.kwargs["state"]
            params = call.kwargs["params"]
            assert isinstance(state, BaseState)
            assert state.to_dict() == {}
            assert isinstance(params, BaseParams)

    @pytest.mark.anyio
    async def test_mode_passed_to_logger(self, machine):
        """Проверяем, что mode из конструктора попадает в scope логера."""
        machine_with_mode = ActionProductMachine(
            context=Context(),
            mode="staging",
            log_coordinator=AsyncMock(spec=LogCoordinator)
        )
        machine_with_mode._log_coordinator.emit = AsyncMock()

        await machine_with_mode.run(ActionWithAspects(), MockParams())

        scope = machine_with_mode._log_coordinator.emit.call_args_list[0].kwargs["scope"]
        assert scope["mode"] == "staging"