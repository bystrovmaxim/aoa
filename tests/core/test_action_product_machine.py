# tests/core/test_action_product_machine.py
from unittest.mock import MagicMock

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
from action_machine.Core.Exceptions import AuthorizationError, ConnectionValidationError, ValidationFieldError
from action_machine.Plugins.Plugin import Plugin
from action_machine.Plugins.PluginCoordinator import PluginCoordinator
from action_machine.ResourceManagers.BaseResourceManager import BaseResourceManager


# ----------------------------------------------------------------------
# Вспомогательные классы для тестов
# ----------------------------------------------------------------------
class MockParams(BaseParams):
    pass

class MockResult(BaseResult):
    pass

class MockAction(BaseAction[MockParams, MockResult]):
    pass

class MockResourceManager(BaseResourceManager):
    def get_wrapper_class(self):
        return None

# ----------------------------------------------------------------------
# Тестовые действия с разными конфигурациями аспектов
# ----------------------------------------------------------------------
@CheckRoles(CheckRoles.NONE, desc="Без аутентификации")
class ActionWithAspects(MockAction):
    """Действие с несколькими аспектами для проверки порядка."""
    _test_calls = []

    @aspect("Первый аспект")
    @StringFieldChecker("value", "Значение", required=True)
    async def aspect1(self, params, state, deps, connections):
        self._test_calls.append("aspect1")
        # Возвращаем строку — StringFieldChecker требует str
        return {"value": "one"}

    @aspect("Второй аспект")
    @StringFieldChecker("value", "Значение", required=True)
    async def aspect2(self, params, state, deps, connections):
        self._test_calls.append("aspect2")
        return {"value": "two"}

    @summary_aspect("Главный аспект")
    async def summary(self, params, state, deps, connections):
        self._test_calls.append("summary")
        return MockResult()

@CheckRoles(CheckRoles.NONE, desc="Без аутентификации")
class ActionWithoutSummary(MockAction):
    @aspect("Обычный аспект")
    async def aspect(self, params, state, deps, connections):
        return {}

@CheckRoles(CheckRoles.NONE, desc="Без аутентификации")
class ActionWithTwoSummaries(MockAction):
    @summary_aspect("Первый")
    async def summary1(self, params, state, deps, connections):
        return MockResult()

    @summary_aspect("Второй")
    async def summary2(self, params, state, deps, connections):
        return MockResult()

@CheckRoles(CheckRoles.NONE, desc="Без аутентификации")
class ActionWithInheritedAspects(MockAction):
    pass

@CheckRoles(CheckRoles.NONE, desc="Без аутентификации")
class ParentAction(MockAction):
    @aspect("Родительский")
    async def parent_aspect(self, params, state, deps, connections):
        return {}

@CheckRoles(CheckRoles.NONE, desc="Без аутентификации")
class ChildAction(ParentAction):
    @aspect("Дочерний")
    async def child_aspect(self, params, state, deps, connections):
        return {}

    @summary_aspect("Summary")
    async def summary(self, params, state, deps, connections):
        return MockResult()

# ----------------------------------------------------------------------
# Тестовые действия для проверки ролей
# ----------------------------------------------------------------------
@CheckRoles(CheckRoles.NONE, desc="Без аутентификации")
class ActionNone(MockAction):
    @summary_aspect("test")
    async def summary(self, params, state, deps, connections):
        return MockResult()

@CheckRoles(CheckRoles.ANY, desc="Любая роль")
class ActionAny(MockAction):
    @summary_aspect("test")
    async def summary(self, params, state, deps, connections):
        return MockResult()

@CheckRoles("admin", desc="Только админ")
class ActionSingleRole(MockAction):
    @summary_aspect("test")
    async def summary(self, params, state, deps, connections):
        return MockResult()

@CheckRoles(["admin", "manager"], desc="Админ или менеджер")
class ActionListRole(MockAction):
    @summary_aspect("test")
    async def summary(self, params, state, deps, connections):
        return MockResult()

class ActionNoDecorator(MockAction):
    @summary_aspect("test")
    async def summary(self, params, state, deps, connections):
        return MockResult()

# ----------------------------------------------------------------------
# Тестовые действия для проверки connections
# ----------------------------------------------------------------------
@connection("db", MockResourceManager, description="База данных")
@CheckRoles(CheckRoles.NONE, desc="Без аутентификации")
class ActionWithOneConnection(MockAction):
    @summary_aspect("test")
    async def summary(self, params, state, deps, connections):
        assert "db" in connections
        return MockResult()

@connection("db", MockResourceManager)
@connection("cache", MockResourceManager)
@CheckRoles(CheckRoles.NONE, desc="Без аутентификации")
class ActionWithTwoConnections(MockAction):
    @summary_aspect("test")
    async def summary(self, params, state, deps, connections):
        assert "db" in connections
        assert "cache" in connections
        return MockResult()

@CheckRoles(CheckRoles.NONE, desc="Без аутентификации")
class ActionWithoutConnections(MockAction):
    @summary_aspect("test")
    async def summary(self, params, state, deps, connections):
        assert connections == {}
        return MockResult()

# ----------------------------------------------------------------------
# Действия для TestRun — на уровне модуля
# ----------------------------------------------------------------------
@CheckRoles(CheckRoles.NONE, desc="")
class BadAction(MockAction):
    """Аспект возвращает не dict."""
    @aspect("bad")
    async def bad(self, params, state, deps, connections):
        return "not a dict"

    @summary_aspect("summary")
    async def summary(self, params, state, deps, connections):
        return MockResult()

@CheckRoles(CheckRoles.NONE, desc="")
class ActionWithoutCheckers(MockAction):
    """Аспект возвращает непустой dict без чекеров."""
    @aspect("no checkers")
    async def aspect_no_checkers(self, params, state, deps, connections):
        return {"field": "value"}

    @summary_aspect("summary")
    async def summary(self, params, state, deps, connections):
        return MockResult()

@CheckRoles(CheckRoles.NONE, desc="")
class ActionWithChecker(MockAction):
    """Аспект возвращает лишние поля."""
    @aspect("with checker")
    @StringFieldChecker("field", "Тестовое поле", required=True)
    async def aspect_with_checker(self, params, state, deps, connections):
        return {"field": "ok", "extra": "forbidden"}

    @summary_aspect("summary")
    async def summary(self, params, state, deps, connections):
        return MockResult()

# ----------------------------------------------------------------------
# Фикстуры
# ----------------------------------------------------------------------
@pytest.fixture
def context_with_roles():
    user = UserInfo(user_id="test", roles=["user", "admin"])
    return Context(user=user)

@pytest.fixture
def context_without_roles():
    user = UserInfo(user_id="guest", roles=[])
    return Context(user=user)

@pytest.fixture
def machine(context_with_roles):
    return ActionProductMachine(context_with_roles)

@pytest.fixture
def machine_without_roles(context_without_roles):
    return ActionProductMachine(context_without_roles)

@pytest.fixture
def mock_plugin():
    plugin = MagicMock(spec=Plugin)
    plugin.get_handlers.return_value = []
    return plugin

# ======================================================================
# ТЕСТЫ: Сбор аспектов (_collect_aspects)
# ======================================================================
class TestCollectAspects:
    def test_collect_aspects_returns_sorted_regular_and_summary(self):
        machine = ActionProductMachine(Context())
        aspects, summary = machine._collect_aspects(ActionWithAspects)
        assert len(aspects) == 2
        assert aspects[0][0].__name__ == "aspect1"
        assert aspects[1][0].__name__ == "aspect2"
        assert aspects[0][1] == "Первый аспект"
        assert aspects[1][1] == "Второй аспект"
        assert summary.__name__ == "summary"

    def test_collect_aspects_ignores_inherited_methods(self):
        machine = ActionProductMachine(Context())
        aspects, summary = machine._collect_aspects(ChildAction)
        assert len(aspects) == 1
        assert aspects[0][0].__name__ == "child_aspect"
        assert summary.__name__ == "summary"

    def test_collect_aspects_no_summary_raises(self):
        machine = ActionProductMachine(Context())
        with pytest.raises(TypeError, match="не имеет summary_aspect"):
            machine._collect_aspects(ActionWithoutSummary)

    def test_collect_aspects_two_summaries_raises(self):
        machine = ActionProductMachine(Context())
        with pytest.raises(TypeError, match="более одного summary_aspect"):
            machine._collect_aspects(ActionWithTwoSummaries)

    def test_get_aspects_caches_result(self):
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
    def test_none_role_allows_any_user(self, machine_without_roles):
        action = ActionNone()
        machine_without_roles._check_action_roles(action)

    def test_any_role_allows_user_with_roles(self, machine):
        action = ActionAny()
        machine._check_action_roles(action)

    def test_any_role_rejects_user_without_roles(self, machine_without_roles):
        action = ActionAny()
        with pytest.raises(AuthorizationError, match="Требуется аутентификация"):
            machine_without_roles._check_action_roles(action)

    def test_single_role_match(self, machine):
        action = ActionSingleRole()
        machine._check_action_roles(action)

    def test_single_role_no_match(self, machine):
        @CheckRoles("manager", desc="")
        class _ActionManager(MockAction):
            @summary_aspect("test")
            async def summary(self, params, state, deps, connections):
                return MockResult()

        action = _ActionManager()
        with pytest.raises(AuthorizationError, match="Требуется роль: 'manager'"):
            machine._check_action_roles(action)

    def test_list_role_intersection(self, machine):
        action = ActionListRole()
        machine._check_action_roles(action)

    def test_list_role_no_intersection(self, machine):
        @CheckRoles(["manager", "editor"], desc="")
        class _ActionManagerEditor(MockAction):
            @summary_aspect("test")
            async def summary(self, params, state, deps, connections):
                return MockResult()

        action = _ActionManagerEditor()
        with pytest.raises(AuthorizationError, match="Требуется одна из ролей"):
            machine._check_action_roles(action)

    def test_action_without_role_spec_raises_type_error(self, machine):
        action = ActionNoDecorator()
        with pytest.raises(TypeError, match="не имеет декоратора CheckRoles"):
            machine._check_action_roles(action)

# ======================================================================
# ТЕСТЫ: Проверка connections (_check_connections)
# ======================================================================
class TestCheckConnections:
    def test_no_declarations_no_connections_returns_empty_dict(self, machine):
        action = ActionWithoutConnections()
        result = machine._check_connections(action, None)
        assert result == {}

    def test_no_declarations_with_connections_raises(self, machine):
        action = ActionWithoutConnections()
        conns = {"db": MockResourceManager()}
        with pytest.raises(ConnectionValidationError, match="не объявляет @connection, но получило"):
            machine._check_connections(action, conns)

    def test_has_declarations_no_connections_raises(self, machine):
        action = ActionWithOneConnection()
        with pytest.raises(ConnectionValidationError, match="но connections не переданы"):
            machine._check_connections(action, None)

    def test_extra_keys_raises(self, machine):
        action = ActionWithOneConnection()
        conns = {"db": MockResourceManager(), "extra": MockResourceManager()}
        with pytest.raises(ConnectionValidationError, match="лишние connections"):
            machine._check_connections(action, conns)

    def test_missing_keys_raises(self, machine):
        action = ActionWithTwoConnections()
        conns = {"db": MockResourceManager()}
        with pytest.raises(ConnectionValidationError, match="не получило connections"):
            machine._check_connections(action, conns)

    def test_valid_connections_passes(self, machine):
        action = ActionWithTwoConnections()
        conns = {"db": MockResourceManager(), "cache": MockResourceManager()}
        result = machine._check_connections(action, conns)
        assert result == conns

# ======================================================================
# ТЕСТЫ: Полный конвейер run()
# ======================================================================
class TestRun:
    @pytest.mark.anyio
    async def test_run_executes_aspects_in_order(self, machine):
        action = ActionWithAspects()
        params = MockParams()
        ActionWithAspects._test_calls = []
        result = await machine.run(action, params)
        assert ActionWithAspects._test_calls == ["aspect1", "aspect2", "summary"]
        assert isinstance(result, MockResult)

    @pytest.mark.anyio
    async def test_run_aspect_returns_non_dict_raises(self, machine):
        action = BadAction()
        params = MockParams()
        with pytest.raises(TypeError, match="должен возвращать dict"):
            await machine.run(action, params)

    @pytest.mark.anyio
    async def test_run_aspect_returns_dict_without_checkers_raises(self, machine):
        action = ActionWithoutCheckers()
        params = MockParams()
        with pytest.raises(ValidationFieldError, match="не имеет чекеров, но вернул непустой state"):
            await machine.run(action, params)

    @pytest.mark.anyio
    async def test_run_aspect_returns_extra_fields_raises(self, machine):
        action = ActionWithChecker()
        params = MockParams()
        with pytest.raises(ValidationFieldError, match="лишние поля"):
            await machine.run(action, params)

    @pytest.mark.anyio
    async def test_run_calls_plugin_events(self, machine, mock_plugin):
        machine._plugin_coordinator = MagicMock(spec=PluginCoordinator)
        action = ActionWithAspects()
        params = MockParams()
        ActionWithAspects._test_calls = []
        await machine.run(action, params)
        # global_start, before:aspect1, after:aspect1, before:aspect2, after:aspect2, global_finish
        assert machine._plugin_coordinator.emit_event.call_count == 6

    @pytest.mark.anyio
    async def test_nest_level_increments_and_decrements(self, machine):
        assert machine._nest_level == 0
        action = ActionWithAspects()
        params = MockParams()
        ActionWithAspects._test_calls = []
        await machine.run(action, params)
        assert machine._nest_level == 0

    @pytest.mark.anyio
    async def test_nest_level_passed_to_plugins(self, machine, mock_plugin):
        machine._plugin_coordinator = MagicMock(spec=PluginCoordinator)
        action = ActionWithAspects()
        params = MockParams()
        ActionWithAspects._test_calls = []
        await machine.run(action, params)
        calls = machine._plugin_coordinator.emit_event.call_args_list
        # nest_level может передаваться как kwargs ИЛИ как позиционный аргумент
        def has_nest_level_1(call):
            args, kwargs = call
            if kwargs.get("nest_level") == 1:
                return True
            # Проверяем позиционные аргументы — nest_level может быть любым по счёту
            if 1 in args:
                return True
            return False
        assert any(has_nest_level_1(call) for call in calls)