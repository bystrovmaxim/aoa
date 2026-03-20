# tests/core/test_action_product_machine.py
"""
Tests for ActionProductMachine — the main action machine.

Checks:
- Aspect collection (_collect_aspects)
- Role checking (_check_action_roles)
- Connection checking (_check_connections)
- Full run() pipeline including logging
- Passing of mode and log parameters to aspects
- All aspects must accept log (sixth parameter)
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from action_machine.aspects.regular_aspect import regular_aspect
from action_machine.aspects.summary_aspect import summary_aspect
from action_machine.Auth.check_roles import CheckRoles
from action_machine.Checkers.StringFieldChecker import StringFieldChecker
from action_machine.Context.context import Context
from action_machine.Context.user_info import UserInfo
from action_machine.Core.ActionProductMachine import ActionProductMachine
from action_machine.Core.AspectMethod import connection
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
# Helper classes
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
# Actions: aspect configurations (ALL with log parameter)
# ----------------------------------------------------------------------
@CheckRoles(CheckRoles.NONE, desc="No authentication")
class ActionWithAspects(MockAction):
    """Action with several aspects to verify order and logging."""
    _test_calls: list[str] = []

    @regular_aspect("First aspect")
    @StringFieldChecker("value", "Value", required=True)
    async def aspect1(
        self,
        params: MockParams,
        state: BaseState,
        deps: dict,
        connections: dict,
        log: ActionBoundLogger,
    ) -> dict:
        self._test_calls.append("aspect1")
        await log.info("Aspect1 executed", value="one")
        return {"value": "one"}

    @regular_aspect("Second aspect")
    @StringFieldChecker("value", "Value", required=True)
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

    @summary_aspect("Main aspect")
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


@CheckRoles(CheckRoles.NONE, desc="No authentication")
class ParentAction(MockAction):
    @regular_aspect("Parent")
    async def parent_aspect(
        self,
        params: MockParams,
        state: BaseState,
        deps: dict,
        connections: dict,
        log: ActionBoundLogger,
    ) -> dict:
        return {}


@CheckRoles(CheckRoles.NONE, desc="No authentication")
class ChildAction(ParentAction):
    @regular_aspect("Child")
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
# Actions: role checking
# ----------------------------------------------------------------------
@CheckRoles(CheckRoles.NONE, desc="No authentication")
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


@CheckRoles(CheckRoles.ANY, desc="Any role")
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


@CheckRoles("admin", desc="Only admin")
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


@CheckRoles(["admin", "manager"], desc="Admin or manager")
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
# Actions: connection checking
# ----------------------------------------------------------------------
@connection("db", MockResourceManager, description="Database")
@CheckRoles(CheckRoles.NONE, desc="No authentication")
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
@CheckRoles(CheckRoles.NONE, desc="No authentication")
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


@CheckRoles(CheckRoles.NONE, desc="No authentication")
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
# Actions for TestRun (errors etc.)
# ----------------------------------------------------------------------
@CheckRoles(CheckRoles.NONE, desc="")
class BadAction(MockAction):
    """Aspect returns non-dict."""

    @regular_aspect("bad")
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
    """Aspect returns non-empty dict without checkers."""

    @regular_aspect("no checkers")
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
    """Aspect returns extra fields."""

    @regular_aspect("with checker")
    @StringFieldChecker("field", "Test field", required=True)
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
# Fixtures
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
    """Machine with mode 'production' and mock log coordinator to verify calls."""
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
# TESTS: Constructor and parameters
# ======================================================================
class TestConstructor:
    def test_mode_must_be_non_empty(self):
        """mode cannot be empty."""
        with pytest.raises(ValueError, match="mode must be non-empty"):
            ActionProductMachine(mode="")

    def test_default_log_coordinator_created(self):
        """If log_coordinator is not provided, one with ConsoleLogger is created."""
        machine = ActionProductMachine(mode="test")
        assert machine._log_coordinator is not None
        from action_machine.Logging.log_coordinator import LogCoordinator
        assert isinstance(machine._log_coordinator, LogCoordinator)


# ======================================================================
# TESTS: Aspect collection is now handled by AspectGateHost, but we test that
#        get_aspects() works correctly through the action.
# ======================================================================
class TestGetAspects:
    def test_get_aspects_returns_sorted_regular_and_summary(self):
        action = ActionWithAspects()
        regular, summary = action.get_aspects()
        assert len(regular) == 2
        assert regular[0][0].__name__ == "aspect1"
        assert regular[1][0].__name__ == "aspect2"
        assert regular[0][1] == "First aspect"
        assert regular[1][1] == "Second aspect"
        assert summary is not None
        assert summary[0].__name__ == "summary"
        assert summary[1] == "Main aspect"

    def test_get_aspects_ignores_inherited_methods(self):
        action = ChildAction()
        regular, summary = action.get_aspects()
        assert len(regular) == 1
        assert regular[0][0].__name__ == "child_aspect"
        assert summary is not None
        assert summary[0].__name__ == "summary"

    def test_get_aspects_no_summary_raises(self):
        class ActionNoSummary(MockAction):
            @regular_aspect("no summary")
            async def aspect(self, params, state, deps, connections, log):
                return {}

        with pytest.raises(TypeError, match="does not have a summary aspect"):
            ActionNoSummary()  # создаём экземпляр – здесь возникает ошибка

    def test_get_aspects_two_summaries_raises(self):
        with pytest.raises(TypeError, match="Only one summary aspect can be registered per action"):
            class ActionTwoSummaries(MockAction):
                @summary_aspect("first")
                async def summary1(self, params, state, deps, connections, log):
                    return MockResult()

                @summary_aspect("second")
                async def summary2(self, params, state, deps, connections, log):
                    return MockResult()


# ======================================================================
# TESTS: Role checking (_check_action_roles)
# ======================================================================
class TestCheckActionRoles:
    def test_none_role_allows_any_user(self, machine, context_without_roles):
        machine._check_action_roles(ActionNone(), context_without_roles)

    def test_any_role_allows_user_with_roles(self, machine, context_with_roles):
        machine._check_action_roles(ActionAny(), context_with_roles)

    def test_any_role_rejects_user_without_roles(self, machine, context_without_roles):
        with pytest.raises(AuthorizationError, match="Authentication required: user must have at least one role"):
            machine._check_action_roles(ActionAny(), context_without_roles)

    def test_single_role_match(self, machine, context_with_roles):
        machine._check_action_roles(ActionSingleRole(), context_with_roles)

    def test_single_role_no_match(self, machine, context_with_roles):
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

        with pytest.raises(AuthorizationError, match="Access denied. Required role: 'manager'"):
            machine._check_action_roles(_ActionManager(), context_with_roles)

    def test_list_role_intersection(self, machine, context_with_roles):
        machine._check_action_roles(ActionListRole(), context_with_roles)

    def test_list_role_no_intersection(self, machine, context_with_roles):
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

        with pytest.raises(AuthorizationError, match="Access denied. Required one of the roles:"):
            machine._check_action_roles(_ActionManagerEditor(), context_with_roles)

    def test_action_without_role_spec_raises_type_error(self, machine, context_with_roles):
        with pytest.raises(TypeError, match="does not have a CheckRoles decorator"):
            machine._check_action_roles(ActionNoDecorator(), context_with_roles)


# ======================================================================
# TESTS: Connection checking (_check_connections)
# ======================================================================
class TestCheckConnections:
    def test_no_declarations_no_connections_returns_empty_dict(self, machine):
        result = machine._check_connections(ActionWithoutConnections(), None)
        assert result == {}

    def test_no_declarations_with_connections_raises(self, machine):
        conns = {"db": MockResourceManager()}
        with pytest.raises(ConnectionValidationError, match="does not declare any @connection, but received connections with keys:"):
            machine._check_connections(ActionWithoutConnections(), conns)

    def test_has_declarations_no_connections_raises(self, machine):
        with pytest.raises(ConnectionValidationError, match="declares connections: .*, but no connections were passed"):
            machine._check_connections(ActionWithOneConnection(), None)

    def test_extra_keys_raises(self, machine):
        conns = {"db": MockResourceManager(), "extra": MockResourceManager()}
        with pytest.raises(ConnectionValidationError, match="received extra connections:"):
            machine._check_connections(ActionWithOneConnection(), conns)

    def test_missing_keys_raises(self, machine):
        conns = {"db": MockResourceManager()}
        with pytest.raises(ConnectionValidationError, match="is missing required connections:"):
            machine._check_connections(ActionWithTwoConnections(), conns)

    def test_valid_connections_passes(self, machine):
        conns = {"db": MockResourceManager(), "cache": MockResourceManager()}
        result = machine._check_connections(ActionWithTwoConnections(), conns)
        assert result == conns


# ======================================================================
# TESTS: Full run() pipeline
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
        with pytest.raises(ValidationFieldError, match="returned extra fields:"):
            await machine.run(context_with_roles, ActionWithChecker(), MockParams())

    @pytest.mark.anyio
    async def test_run_calls_plugin_events(self, machine, context_with_roles, mock_plugin):
        # Replace plugin coordinator with mock
        machine._plugin_coordinator = AsyncMock(spec=PluginCoordinator)
        ActionWithAspects._test_calls = []
        await machine.run(context_with_roles, ActionWithAspects(), MockParams())
        # global_start, before:aspect1, after:aspect1, before:aspect2, after:aspect2, global_finish
        assert machine._plugin_coordinator.emit_event.await_count == 6

    @pytest.mark.anyio
    async def test_nest_level_increments_and_decrements(self, machine, context_with_roles):
        assert machine._nest_level == 0
        ActionWithAspects._test_calls = []
        await machine.run(context_with_roles, ActionWithAspects(), MockParams())
        assert machine._nest_level == 0

    # ------------------------------------------------------------------
    # TESTS: Logging and mode passing
    # ------------------------------------------------------------------
    @pytest.mark.anyio
    async def test_logger_passed_to_aspects(self, machine, context_with_roles):
        """Check that log.emit is called in each aspect."""
        ActionWithAspects._test_calls = []
        await machine.run(context_with_roles, ActionWithAspects(), MockParams())
        assert machine._log_coordinator.emit.await_count >= 3

    @pytest.mark.anyio
    async def test_logger_receives_correct_scope(self, machine, context_with_roles):
        """Check that the log scope is formed correctly."""
        machine._log_coordinator.emit = AsyncMock()
        await machine.run(context_with_roles, ActionWithAspects(), MockParams())
        call_args = machine._log_coordinator.emit.call_args_list[0]
        scope = call_args.kwargs["scope"]
        assert scope["machine"] == "ActionProductMachine"
        assert scope["mode"] == "production"
        assert scope["action"] == "tests.core.test_action_product_machine.ActionWithAspects"
        assert scope["aspect"] == "aspect1"
        assert list(scope.keys()) == ["machine", "mode", "action", "aspect"]

    @pytest.mark.anyio
    async def test_logger_receives_correct_indent(self, machine, context_with_roles):
        machine._log_coordinator.emit = AsyncMock()
        await machine.run(context_with_roles, ActionWithAspects(), MockParams())
        for call in machine._log_coordinator.emit.call_args_list:
            indent = call.kwargs["indent"]
            assert indent == 1

    @pytest.mark.anyio
    async def test_logger_passed_empty_state_and_params(self, machine, context_with_roles):
        machine._log_coordinator.emit = AsyncMock()
        await machine.run(context_with_roles, ActionWithAspects(), MockParams())
        for call in machine._log_coordinator.emit.call_args_list:
            state = call.kwargs["state"]
            params = call.kwargs["params"]
            assert isinstance(state, BaseState)
            assert state.to_dict() == {}
            assert isinstance(params, BaseParams)

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