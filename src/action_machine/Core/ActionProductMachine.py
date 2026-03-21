# src/action_machine/Core/ActionProductMachine.py
"""
Product action machine implementation with plugin support and nesting.
Fully asynchronous version. Uses PluginEvent to pass data to plugins.

Изменения (этап 3):
- Убран кэш аспектов (`_aspect_cache`) – теперь кэширование выполняется в `AspectGateHost`.
- Вызовы `self._get_aspects(action)` заменены на `action.get_aspects()`.
- Удалён метод `_get_aspects` (больше не нужен).
- Обновлены комментарии.
"""

import time
from collections.abc import Callable
from typing import Any, TypeVar, cast

from action_machine.aspects.aspect_method_protocol import AspectMethodProtocol
from action_machine.Auth.check_roles import CheckRoles
from action_machine.Context.context import Context
from action_machine.Core.BaseAction import BaseAction
from action_machine.Core.BaseActionMachine import BaseActionMachine
from action_machine.Core.BaseParams import BaseParams
from action_machine.Core.BaseResult import BaseResult
from action_machine.Core.BaseState import BaseState
from action_machine.Core.DependencyFactory import DependencyFactory
from action_machine.Core.Exceptions import AuthorizationError, ConnectionValidationError, ValidationFieldError
from action_machine.Core.ToolsBox import ToolsBox
from action_machine.Logging.action_bound_logger import ActionBoundLogger
from action_machine.Logging.console_logger import ConsoleLogger
from action_machine.Logging.log_coordinator import LogCoordinator
from action_machine.Plugins.Plugin import Plugin
from action_machine.Plugins.PluginCoordinator import PluginCoordinator
from action_machine.ResourceManagers.BaseResourceManager import BaseResourceManager

P = TypeVar("P", bound=BaseParams)
R = TypeVar("R", bound=BaseResult)


class ActionProductMachine(BaseActionMachine):
    """
    Product implementation of the action machine (asynchronous).

    Contains logic for caching dependency factories,
    performs role checking, validation of aspect results through checkers,
    and checks the correspondence of passed connections to those declared with @connection.

    Plugin management is delegated to PluginCoordinator.

    The machine does **not** store per‑request context; context must be passed
    to the `run()` method for each execution.
    """

    def __init__(
        self,
        mode: str,
        plugins: list[Plugin] | None = None,
        log_coordinator: LogCoordinator | None = None,
    ) -> None:
        """
        Initializes the action machine.

        Args:
            mode: execution mode (required, non-empty). Examples: "production", "test", "staging".
            plugins: list of plugin instances (default empty).
            log_coordinator: logging coordinator. If not specified, a
                             coordinator with a single ConsoleLogger(use_colors=True) is created.

        Raises:
            ValueError: if mode is an empty string.
        """
        if not mode:
            raise ValueError("mode must be non-empty")
        self._mode = mode

        # Plugin coordinator
        self._plugin_coordinator: PluginCoordinator = PluginCoordinator(
            plugins=plugins or [],
        )

        # Logging coordinator
        if log_coordinator is None:
            log_coordinator = LogCoordinator(loggers=[ConsoleLogger(use_colors=True)])
        self._log_coordinator = log_coordinator

        # Dependency factory cache
        self._factory_cache: dict[type[Any], DependencyFactory] = {}

    def _get_factory(self, action_class: type[Any]) -> DependencyFactory:
        """Returns (and caches) the dependency factory for the action class."""
        if action_class not in self._factory_cache:
            deps_info = getattr(action_class, "_dependencies", [])
            self._factory_cache[action_class] = DependencyFactory(deps_info)
        return self._factory_cache[action_class]

    def _apply_checkers(
        self,
        method: Callable[..., Any],
        result: dict[str, Any],
    ) -> None:
        """Applies checkers attached to the method to the result dict."""
        checkers = getattr(method, "_result_checkers", [])
        for checker in checkers:
            checker.check(result)

    # ---------- Role checking ----------

    def _check_none_role(self, user_roles: list[str]) -> bool:
        """Check for CheckRoles.NONE (always allowed)."""
        return True

    def _check_any_role(self, user_roles: list[str]) -> bool:
        """Check for CheckRoles.ANY (requires at least one role)."""
        if not user_roles:
            raise AuthorizationError("Authentication required: user must have at least one role")
        return True

    def _check_list_role(self, spec: list[str], user_roles: list[str]) -> bool:
        """Check for a list of roles (intersection)."""
        if any(role in user_roles for role in spec):
            return True
        raise AuthorizationError(
            f"Access denied. Required one of the roles: {spec}, user roles: {user_roles}"
        )

    def _check_single_role(self, spec: str, user_roles: list[str]) -> bool:
        """Check for a single specific role."""
        if spec in user_roles:
            return True
        raise AuthorizationError(f"Access denied. Required role: '{spec}', user roles: {user_roles}")

    def _check_action_roles(self, action: BaseAction[P, R], context: Context) -> None:
        """
        Checks that the action has a role specification (CheckRoles decorator)
        and that the current user from the context satisfies it.

        Args:
            action: action instance.
            context: execution context containing user information.

        Raises:
            TypeError: if the action does not have a _role_spec attribute.
            AuthorizationError: if the user's roles do not meet the requirements.
        """
        role_spec = getattr(action.__class__, "_role_spec", None)
        if role_spec is None:
            raise TypeError(
                f"Action {action.__class__.__name__} does not have a CheckRoles decorator. "
                "Specify CheckRoles.NONE explicitly if the action is accessible without authentication."
            )
        user_roles = context.user.roles

        if role_spec == CheckRoles.NONE:
            self._check_none_role(user_roles)
        elif role_spec == CheckRoles.ANY:
            self._check_any_role(user_roles)
        elif isinstance(role_spec, list):
            self._check_list_role(role_spec, user_roles)
        else:
            self._check_single_role(role_spec, user_roles)

    # ---------- Connection checking ----------

    @staticmethod
    def _get_declared_connection_keys(action: BaseAction[P, R]) -> set[str]:
        declared: list[dict[str, Any]] = getattr(action.__class__, "_connections", [])
        return {info["key"] for info in declared}

    @staticmethod
    def _validate_no_declarations_but_got_connections(
        action_name: str, declared_keys: set[str], actual_keys: set[str]
    ) -> str | None:
        if not declared_keys and actual_keys:
            return (f"Action {action_name} does not declare any @connection, "
                    f"but received connections with keys: {actual_keys}. "
                    f"Remove the connections from the call or add the @connection decorator.")
        return None

    @staticmethod
    def _validate_has_declarations_but_no_connections(
        action_name: str, declared_keys: set[str], actual_keys: set[str]
    ) -> str | None:
        if declared_keys and not actual_keys:
            return (f"Action {action_name} declares connections: {declared_keys}, "
                    f"but no connections were passed (None or empty dict). "
                    f"Pass connections with keys: {declared_keys}.")
        return None

    @staticmethod
    def _validate_extra_connection_keys(
        action_name: str, declared_keys: set[str], actual_keys: set[str]
    ) -> str | None:
        extra = actual_keys - declared_keys
        if extra:
            return (f"Action {action_name} received extra connections: {extra}. "
                    f"Only declared: {declared_keys}. Remove the extra keys.")
        return None

    @staticmethod
    def _validate_missing_connection_keys(
        action_name: str, declared_keys: set[str], actual_keys: set[str]
    ) -> str | None:
        missing = declared_keys - actual_keys
        if missing:
            return (f"Action {action_name} is missing required connections: {missing}. "
                    f"Declared: {declared_keys}, received: {actual_keys}.")
        return None

    def _check_connections(
        self, action: BaseAction[P, R], connections: dict[str, BaseResourceManager] | None
    ) -> dict[str, BaseResourceManager]:
        """
        Checks that the passed connections match those declared with @connection.

        Args:
            action: action instance.
            connections: connections dictionary (or None).

        Returns:
            Validated connections (empty dict if None and no declarations).

        Raises:
            ConnectionValidationError: if there is a mismatch.
        """
        declared_keys = self._get_declared_connection_keys(action)
        actual_keys = set(connections.keys()) if connections else set()
        action_name = action.__class__.__name__

        for validator in [
            self._validate_no_declarations_but_got_connections,
            self._validate_has_declarations_but_no_connections,
            self._validate_extra_connection_keys,
            self._validate_missing_connection_keys,
        ]:
            error = validator(action_name, declared_keys, actual_keys)
            if error:
                raise ConnectionValidationError(error)
        return connections or {}

    # ---------- Main asynchronous run methods ----------

    async def run(
        self,
        context: Context,
        action: BaseAction[P, R],
        params: P,
        connections: dict[str, BaseResourceManager] | None = None,
    ) -> R:
        """
        Asynchronously executes the action with plugins and nesting support.

        This is the public entry point. Resources are not accepted here;
        they are passed implicitly through the action's dependencies.

        Execution sequence:
            1. Increase nesting level.
            2. Check roles (CheckRoles decorator) using the provided context.
            3. Check connections (@connection decorator).
            4. global_start event (plugins through PluginCoordinator).
            5. Execute regular aspects (with before/after calls).
            6. Execute summary aspect.
            7. global_finish event with total duration.
            8. Decrease nesting level.

        Args:
            context: execution context for this request (user, request, environment).
            action: action instance.
            params: input parameters.
            connections: dictionary of resource managers (connections).

        Returns:
            Result of the action execution.
        """
        return await self._run_internal(context, action, params, resources=None, connections=connections, nested_level=0)

    async def _run_internal(
        self,
        context: Context,
        action: BaseAction[P, R],
        params: P,
        resources: dict[type[Any], Any] | None,
        connections: dict[str, BaseResourceManager] | None,
        nested_level: int,
    ) -> R:
        """
        Internal execution method that handles nesting and resource passing.

        Args:
            context: execution context.
            action: action instance.
            params: input parameters.
            resources: external resources for dependencies (priority over factory).
            connections: resource managers.
            nested_level: current nesting level (0 for root).

        Returns:
            Action result.
        """
        current_nest = nested_level + 1
        start_time = time.time()

        try:
            self._check_action_roles(action, context)
            conns = self._check_connections(action, connections)
            factory = self._get_factory(action.__class__)

            # Create logger for this level
            log = ActionBoundLogger(
                coordinator=self._log_coordinator,
                nest_level=current_nest,
                machine_name=self.__class__.__name__,
                mode=self._mode,
                action_name=action.get_full_class_name(),
                aspect_name="",  # will be set per aspect
                context=context,
            )

            # Create a closure for running child actions.
            async def run_child(
                action: BaseAction[Any, Any],
                params: BaseParams,
                connections: dict[str, BaseResourceManager] | None,
            ) -> BaseResult:
                return await self._run_internal(
                    context=context,
                    action=action,
                    params=params,
                    resources=resources,
                    connections=connections,
                    nested_level=current_nest,
                )

            # Create ToolsBox for this level
            box = ToolsBox(
                run_child=run_child,
                factory=factory,
                resources=resources,
                context=context,
                log=log,
                nested_level=current_nest,
            )

            await self._plugin_coordinator.emit_event(
                event_name="global_start",
                action=action,
                params=params,
                state_aspect=None,
                is_summary=False,
                result=None,
                duration=None,
                factory=factory,
                context=context,
                nest_level=current_nest,
            )

            # Retrieve aspects directly from the action (cached inside AspectGateHost)
            regular_aspects, summary_method = action.get_aspects()
            state = await self._execute_regular_aspects(
                action, params, box, conns, context, regular_aspects
            )

            result = await self._call_aspect(
                summary_method[0] if summary_method else None,
                action, params, state, box, conns, context
            )

            total_duration = time.time() - start_time

            await self._plugin_coordinator.emit_event(
                event_name="global_finish",
                action=action,
                params=params,
                state_aspect=state.to_dict(),
                is_summary=False,
                result=result,
                duration=total_duration,
                factory=factory,
                context=context,
                nest_level=current_nest,
            )

            return cast(R, result)
        finally:
            pass

    async def _call_aspect(
        self,
        method: AspectMethodProtocol | None,
        action: BaseAction[Any, Any],
        params: BaseParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
        context: Context,
    ) -> Any:
        """
        Calls an aspect method.

        The aspect receives `box` as its fifth argument (after connections)
        and uses it for dependency resolution, logging, and running child actions.

        Args:
            method: aspect method to call (None means no summary).
            action: action instance.
            params: input parameters.
            state: current pipeline state.
            box: ToolsBox instance for this level.
            connections: dictionary of resource managers.
            context: execution context (used for logging).

        Returns:
            Result of the aspect (or empty BaseResult if no summary).
        """
        if method is None:
            return BaseResult()

        # Create a logger with the aspect name for this specific call
        aspect_log = ActionBoundLogger(
            coordinator=self._log_coordinator,
            nest_level=box.nested_level,
            machine_name=self.__class__.__name__,
            mode=self._mode,
            action_name=action.get_full_class_name(),
            aspect_name=method.__name__,
            context=context,
        )
        # Create a new box with the aspect-specific logger.
        aspect_box = ToolsBox(
            run_child=box.run_child,
            factory=box.factory,
            resources=box.resources,
            context=box.context,
            log=aspect_log,
            nested_level=box.nested_level,
        )
        return await method(action, params, state, aspect_box, connections)

    async def _execute_regular_aspects(
        self,
        action: BaseAction[P, R],
        params: P,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
        context: Context,
        regular_aspects: list[tuple[AspectMethodProtocol, str]],
    ) -> BaseState:
        """
        Asynchronously executes the chain of regular aspects, calling
        before and after plugin events for each through the coordinator.

        For each aspect:
            - call plugin before-event,
            - execute the aspect itself,
            - check the result through checkers,
            - call plugin after-event with duration.
        """
        state = BaseState()

        for method, description in regular_aspects:
            aspect_name = method.__name__

            await self._plugin_coordinator.emit_event(
                event_name=f"before:{aspect_name}",
                action=action,
                params=params,
                state_aspect=state.to_dict(),
                is_summary=False,
                result=None,
                duration=None,
                factory=box.factory,
                context=context,
                nest_level=box.nested_level,
            )

            aspect_start = time.time()
            # Create aspect-specific box with correct aspect name in log
            aspect_log = ActionBoundLogger(
                coordinator=self._log_coordinator,
                nest_level=box.nested_level,
                machine_name=self.__class__.__name__,
                mode=self._mode,
                action_name=action.get_full_class_name(),
                aspect_name=aspect_name,
                context=context,
            )
            aspect_box = ToolsBox(
                run_child=box.run_child,
                factory=box.factory,
                resources=box.resources,
                context=box.context,
                log=aspect_log,
                nested_level=box.nested_level,
            )
            new_state_dict = await self._call_aspect(method, action, params, state, aspect_box, connections, context)
            if not isinstance(new_state_dict, dict):
                raise TypeError(
                    f"Aspect {method.__qualname__} must return a dict, got {type(new_state_dict).__name__}"
                )

            checkers = getattr(method, "_result_checkers", [])

            if not checkers and new_state_dict:
                raise ValidationFieldError(
                    f"Aspect {method.__qualname__} has no checkers, "
                    f"but returned non-empty state: {new_state_dict}. "
                    f"Either add checkers for all fields, or return an empty dict."
                )

            if checkers:
                allowed_fields = {ch.field_name for ch in checkers}
                extra_fields = set(new_state_dict.keys()) - allowed_fields
                if extra_fields:
                    raise ValidationFieldError(
                        f"Aspect {method.__qualname__} returned extra fields: "
                        f"{extra_fields}. Allowed only: {allowed_fields}"
                    )
                self._apply_checkers(method, new_state_dict)

            state = BaseState(new_state_dict)

            aspect_duration = time.time() - aspect_start

            await self._plugin_coordinator.emit_event(
                event_name=f"after:{aspect_name}",
                action=action,
                params=params,
                state_aspect=state.to_dict(),
                is_summary=False,
                result=None,
                duration=aspect_duration,
                factory=box.factory,
                context=context,
                nest_level=box.nested_level,
            )

        return state