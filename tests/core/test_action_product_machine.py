# tests/core/test_action_product_machine.py
from unittest.mock import MagicMock
from typing import Optional
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
# Действия: конфигурации аспектов
# ----------------------------------------------------------------------
@CheckRoles(CheckRoles.NONE, desc="Без аутентификации")
class ActionWithAspects(MockAction):
    """Действие с несколькими аспектами для проверки порядка."""
    _test_calls: list[str] = []

    @aspect("Первый аспект")
    @StringFieldChecker("value", "Значение", required=True)
    async def aspect1(
        self,
        params: MockParams,
        state: BaseState,
        deps: dict,
        connections: dict,
    ) -> dict:
        self._test_calls.append("aspect1")
        return {"value": "one"}  # StringFieldChecker требует str

    @aspect("Второй аспект")
    @StringFieldChecker("value", "Значение", required=True)
    async def aspect2(
        self,
        params: MockParams,
        state: BaseState,
        deps: dict,
        connections: dict,
    ) -> dict:
        self._test_calls.append("aspect2")
        return {"value": "two"}

    @summary_aspect("Главный аспект")
    async def summary(
        self,
        params: MockParams,
        state: BaseState,
        deps: dict,
        connections: dict,
    ) -> MockResult:
        self._test_calls.append("summary")
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
    ) -> MockResult:
        return MockResult()

    @summary_aspect("Второй")
    async def summary2(
        self,
        params: MockParams,
        state: BaseState,
        deps: dict,
        connections: dict,
    ) -> MockResult:
        return MockResult()

@CheckRoles(CheckRoles.NONE, desc="Без аутентификации")
class ActionWithInheritedAspects(MockAction):
    pass

@CheckRoles(CheckRoles.NONE, desc="Без аутентификации")
class ParentAction(MockAction):
    @aspect("Родительский")
    async def parent_aspect(
        self,
        params: MockParams,
        state: BaseState,
        deps: dict,
        connections: dict,
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
    ) -> dict:
        return {}

    @summary_aspect("Summary")
    async def summary(
        self,
        params: MockParams,
        state: BaseState,
        deps: dict,
        connections: dict,
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
    ) -> MockResult:
        assert connections == {}
        return MockResult()

# ----------------------------------------------------------------------
# Действия для TestRun
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
    ) -> str:
        return "not a dict"

    @summary_aspect("summary")
    async def summary(
        self,
        params: MockParams,
        state: BaseState,
        deps: dict,
        connections: dict,
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
    ) -> dict:
        return {"field": "value"}

    @summary_aspect("summary")
    async def summary(
        self,
        params: MockParams,
        state: BaseState,
        deps: dict,
        connections: dict,
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
    ) -> dict:
        return {"field": "ok", "extra": "forbidden"}

    @summary_aspect("summary")
    async def summary(
        self,
        params: MockParams,
        state: BaseState,
        deps: dict,
        connections: dict,
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
    return ActionProductMachine(context_with_roles)

@pytest.fixture
def machine_without_roles(context_without_roles: Context) -> ActionProductMachine:
    return ActionProductMachine(context_without_roles)

@pytest.fixture
def mock_plugin() -> MagicMock:
    plugin = MagicMock(spec=Plugin)
    plugin.get_handlers.return_value = []
    return plugin

# ======================================================================
# ТЕСТЫ: Сбор аспектов (_collect_aspects)
# ======================================================================
class TestCollectAspects:
    def test_collect_aspects_returns_sorted_regular_and_summary(self) -> None:
        machine = ActionProductMachine(Context())
        aspects, summary = machine._collect_aspects(ActionWithAspects)
        assert len(aspects) == 2
        assert aspects[0][0].__name__ == "aspect1"
        assert aspects[1][0].__name__ == "aspect2"
        assert aspects[0][1] == "Первый аспект"
        assert aspects[1][1] == "Второй аспект"
        assert summary.__name__ == "summary"

    def test_collect_aspects_ignores_inherited_methods(self) -> None:
        machine = ActionProductMachine(Context())
        aspects, summary = machine._collect_aspects(ChildAction)
        assert len(aspects) == 1
        assert aspects[0][0].__name__ == "child_aspect"
        assert summary.__name__ == "summary"

    def test_collect_aspects_no_summary_raises(self) -> None:
        machine = ActionProductMachine(Context())
        with pytest.raises(TypeError, match="не имеет summary_aspect"):
            machine._collect_aspects(ActionWithoutSummary)

    def test_collect_aspects_two_summaries_raises(self) -> None:
        machine = ActionProductMachine(Context())
        with pytest.raises(TypeError, match="более одного summary_aspect"):
            machine._collect_aspects(ActionWithTwoSummaries)

    def test_get_aspects_caches_result(self) -> None:
        machine = ActionProductMachine(Context())
        aspects1, summary1 = machine._get_aspects(ActionWithAspects)
        aspects2, summary2 = machine._get_aspects(ActionWithAspects)
        assert aspects1 is aspects2
        assert summary1 is summary2
        assert ActionWithAspects in machine._aspect_cache

# ======================================================================
# ТЕСТЫ: Проверка ролей (_check_action_roles)
# ======================================================================
class TestCheckActionRoles:
    def test_none_role_allows_any_user(self, machine_without_roles: ActionProductMachine) -> None:
        machine_without_roles._check_action_roles(ActionNone())

    def test_any_role_allows_user_with_roles(self, machine: ActionProductMachine) -> None:
        machine._check_action_roles(ActionAny())

    def test_any_role_rejects_user_without_roles(self, machine_without_roles: ActionProductMachine) -> None:
        with pytest.raises(AuthorizationError, match="Требуется аутентификация"):
            machine_without_roles._check_action_roles(ActionAny())

    def test_single_role_match(self, machine: ActionProductMachine) -> None:
        machine._check_action_roles(ActionSingleRole())

    def test_single_role_no_match(self, machine: ActionProductMachine) -> None:
        @CheckRoles("manager", desc="")
        class _ActionManager(MockAction):
            @summary_aspect("test")
            async def summary(
                self,
                params: MockParams,
                state: BaseState,
                deps: dict,
                connections: dict,
            ) -> MockResult:
                return MockResult()

        with pytest.raises(AuthorizationError, match="Требуется роль: 'manager'"):
            machine._check_action_roles(_ActionManager())

    def test_list_role_intersection(self, machine: ActionProductMachine) -> None:
        machine._check_action_roles(ActionListRole())

    def test_list_role_no_intersection(self, machine: ActionProductMachine) -> None:
        @CheckRoles(["manager", "editor"], desc="")
        class _ActionManagerEditor(MockAction):
            @summary_aspect("test")
            async def summary(
                self,
                params: MockParams,
                state: BaseState,
                deps: dict,
                connections: dict,
            ) -> MockResult:
                return MockResult()

        with pytest.raises(AuthorizationError, match="Требуется одна из ролей"):
            machine._check_action_roles(_ActionManagerEditor())

    def test_action_without_role_spec_raises_type_error(self, machine: ActionProductMachine) -> None:
        with pytest.raises(TypeError, match="не имеет декоратора CheckRoles"):
            machine._check_action_roles(ActionNoDecorator())

# ======================================================================
# ТЕСТЫ: Проверка connections (_check_connections)
# ======================================================================
class TestCheckConnections:
    def test_no_declarations_no_connections_returns_empty_dict(
        self, machine: ActionProductMachine
    ) -> None:
        result = machine._check_connections(ActionWithoutConnections(), None)
        assert result == {}

    def test_no_declarations_with_connections_raises(
        self, machine: ActionProductMachine
    ) -> None:
        conns = {"db": MockResourceManager()}
        with pytest.raises(ConnectionValidationError, match="не объявляет @connection, но получило"):
            machine._check_connections(ActionWithoutConnections(), conns)

    def test_has_declarations_no_connections_raises(
        self, machine: ActionProductMachine
    ) -> None:
        with pytest.raises(ConnectionValidationError, match="но connections не переданы"):
            machine._check_connections(ActionWithOneConnection(), None)

    def test_extra_keys_raises(self, machine: ActionProductMachine) -> None:
        conns = {"db": MockResourceManager(), "extra": MockResourceManager()}
        with pytest.raises(ConnectionValidationError, match="лишние connections"):
            machine._check_connections(ActionWithOneConnection(), conns)

    def test_missing_keys_raises(self, machine: ActionProductMachine) -> None:
        conns = {"db": MockResourceManager()}
        with pytest.raises(ConnectionValidationError, match="не получило connections"):
            machine._check_connections(ActionWithTwoConnections(), conns)

    def test_valid_connections_passes(self, machine: ActionProductMachine) -> None:
        conns = {"db": MockResourceManager(), "cache": MockResourceManager()}
        result = machine._check_connections(ActionWithTwoConnections(), conns)
        assert result == conns

# ======================================================================
# ТЕСТЫ: Полный конвейер run()
# ======================================================================
class TestRun:
    @pytest.mark.anyio
    async def test_run_executes_aspects_in_order(self, machine: ActionProductMachine) -> None:
        ActionWithAspects._test_calls = []
        result = await machine.run(ActionWithAspects(), MockParams())
        assert ActionWithAspects._test_calls == ["aspect1", "aspect2", "summary"]
        assert isinstance(result, MockResult)

    @pytest.mark.anyio
    async def test_run_aspect_returns_non_dict_raises(self, machine: ActionProductMachine) -> None:
        with pytest.raises(TypeError, match="должен возвращать dict"):
            await machine.run(BadAction(), MockParams())

    @pytest.mark.anyio
    async def test_run_aspect_returns_dict_without_checkers_raises(
        self, machine: ActionProductMachine
    ) -> None:
        with pytest.raises(ValidationFieldError, match="не имеет чекеров, но вернул непустой state"):
            await machine.run(ActionWithoutCheckers(), MockParams())

    @pytest.mark.anyio
    async def test_run_aspect_returns_extra_fields_raises(
        self, machine: ActionProductMachine
    ) -> None:
        with pytest.raises(ValidationFieldError, match="лишние поля"):
            await machine.run(ActionWithChecker(), MockParams())

    @pytest.mark.anyio
    async def test_run_calls_plugin_events(
        self, machine: ActionProductMachine, mock_plugin: MagicMock
    ) -> None:
        machine._plugin_coordinator = MagicMock(spec=PluginCoordinator)
        ActionWithAspects._test_calls = []
        await machine.run(ActionWithAspects(), MockParams())
        # global_start, before:aspect1, after:aspect1, before:aspect2, after:aspect2, global_finish
        assert machine._plugin_coordinator.emit_event.call_count == 6

    @pytest.mark.anyio
    async def test_nest_level_increments_and_decrements(
        self, machine: ActionProductMachine
    ) -> None:
        assert machine._nest_level == 0
        ActionWithAspects._test_calls = []
        await machine.run(ActionWithAspects(), MockParams())
        assert machine._nest_level == 0

    @pytest.mark.anyio
    async def test_nest_level_passed_to_plugins(
        self, machine: ActionProductMachine, mock_plugin: MagicMock
    ) -> None:
        machine._plugin_coordinator = MagicMock(spec=PluginCoordinator)
        ActionWithAspects._test_calls = []
        await machine.run(ActionWithAspects(), MockParams())
        calls = machine._plugin_coordinator.emit_event.call_args_list

        def has_nest_level_1(call) -> bool:
            args, kwargs = call
            if kwargs.get("nest_level") == 1:
                return True
            # nest_level может быть позиционным аргументом
            if 1 in args:
                return True
            return False

        assert any(has_nest_level_1(call) for call in calls)