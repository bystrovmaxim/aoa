"""
Product action machine implementation with plugin support and nesting.
Fully asynchronous version. Uses PluginEvent to pass data to plugins.

Architectural decisions:
    - Plugin management logic (state initialization, handler caching,
      asynchronous execution) has been moved to a separate class
      PluginCoordinator (action_machine/Plugins/PluginCoordinator.py).
    - ActionProductMachine delegates all plugin calls through
      self._plugin_coordinator.emit_event(...).
    - _check_connections method is split into 4 private validators,
      each checking one specific rule of correspondence between passed
      connections and those declared with @connection.

Public API of the class:
    - Constructor accepts mode (required), plugins, log_coordinator.
    - Asynchronous method run(...) executes the action with the given context.
"""

import inspect
import time
from collections.abc import Callable
from typing import Any, TypeVar, cast

from action_machine.Auth.check_roles import CheckRoles
from action_machine.Context.context import Context
from action_machine.Core.AspectMethod import AspectMethod
from action_machine.Core.BaseAction import BaseAction
from action_machine.Core.BaseActionMachine import BaseActionMachine
from action_machine.Core.BaseParams import BaseParams
from action_machine.Core.BaseResult import BaseResult
from action_machine.Core.BaseState import BaseState
from action_machine.Core.DependencyFactory import DependencyFactory
from action_machine.Core.Exceptions import AuthorizationError, ConnectionValidationError, ValidationFieldError
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

    Contains logic for caching aspects and dependency factories,
    performs role checking, validation of aspect results through checkers,
    and checks the correspondence of passed connections to those declared with @connection.

    Plugin management is delegated to PluginCoordinator —
    a separate class responsible for state initialization,
    handler caching, and asynchronous execution.

    The machine does **not** store per‑request context; context must be passed
    to the `run()` method for each execution.

    New: end-to-end logging support. The constructor accepts:
        mode (str) – execution mode (e.g., "production", "test", "staging").
        log_coordinator (LogCoordinator | None) – logging coordinator.
            If not provided, a coordinator with ConsoleLogger(use_colors=True) is created.
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

        # Aspect cache
        self._aspect_cache: dict[type[Any], tuple[list[tuple[AspectMethod, str]], AspectMethod]] = {}

        # Dependency factory cache
        self._factory_cache: dict[type[Any], DependencyFactory] = {}

        # Nesting level
        self._nest_level: int = 0

    # ---------- Helper methods for aspects ----------

    def _get_aspects(self, action_class: type[Any]) -> tuple[list[tuple[AspectMethod, str]], AspectMethod]:
        """Returns (list of regular aspects, summary aspect) for the action class. Uses cache."""
        if action_class not in self._aspect_cache:
            aspects, summary = self._collect_aspects(action_class)
            self._aspect_cache[action_class] = (aspects, summary)
        return self._aspect_cache[action_class]

    def _process_method_for_aspect(
        self, method: Any, aspects: list[tuple[AspectMethod, str]], summary_method: AspectMethod | None
    ) -> tuple[list[tuple[AspectMethod, str]], AspectMethod | None]:
        """Processes one method of the class: if it is an aspect, adds it to the corresponding list."""
        if not hasattr(method, "_is_aspect") or not method._is_aspect:
            return aspects, summary_method

        asp_method = cast(AspectMethod, method)
        if asp_method._aspect_type == "regular":
            aspects.append((asp_method, asp_method._aspect_description))
        elif asp_method._aspect_type == "summary":
            if summary_method is not None:
                raise TypeError("Class has more than one summary_aspect")
            summary_method = asp_method
        else:
            raise TypeError(f"Unknown aspect type: {asp_method._aspect_type}")
        return aspects, summary_method

    def _collect_aspects(self, action_class: type[Any]) -> tuple[list[tuple[AspectMethod, str]], AspectMethod]:
        """Collects aspects from the action class (only those defined directly in the class)."""
        aspects: list[tuple[AspectMethod, str]] = []
        summary_method: AspectMethod | None = None

        for _, method in inspect.getmembers(action_class, predicate=inspect.isfunction):
            if method.__qualname__.split(".")[0] != action_class.__name__:
                continue
            aspects, summary_method = self._process_method_for_aspect(method, aspects, summary_method)

        if summary_method is None:
            raise TypeError(f"Class {action_class.__name__} does not have a summary_aspect")

        aspects.sort(key=lambda item: item[0].__code__.co_firstlineno)
        return aspects, summary_method

    def _get_factory(
        self, action_class: type[Any], external_resources: dict[type[Any], Any] | None = None
    ) -> DependencyFactory:
        """Returns (and caches) the dependency factory for the action class."""
        if external_resources is not None:
            deps_info = getattr(action_class, "_dependencies", [])
            return DependencyFactory(self, deps_info, external_resources)
        if action_class not in self._factory_cache:
            deps_info = getattr(action_class, "_dependencies", [])
            self._factory_cache[action_class] = DependencyFactory(self, deps_info, external_resources=None)
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

    # ---------- Main asynchronous run method ----------

    async def run(
        self,
        context: Context,
        action: BaseAction[P, R],
        params: P,
        resources: dict[type[Any], Any] | None = None,
        connections: dict[str, BaseResourceManager] | None = None,
    ) -> R:
        """
        Asynchronously executes the action with plugins and nesting support.

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
            resources: dictionary of external resources (passed to the factory).
            connections: dictionary of resource managers (connections).
        """
        self._nest_level += 1
        start_time = time.time()

        try:
            self._check_action_roles(action, context)
            conns = self._check_connections(action, connections)
            factory = self._get_factory(action.__class__, external_resources=resources)

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
                nest_level=self._nest_level,
            )

            state = await self._execute_regular_aspects(action, params, factory, conns, context)

            _, summary_method = self._get_aspects(action.__class__)
            result = await self._call_aspect(summary_method, action, params, state, factory, conns, context)

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
                nest_level=self._nest_level,
            )

            return cast(R, result)
        finally:
            self._nest_level -= 1

    async def _call_aspect(
        self,
        method: AspectMethod,
        action: BaseAction[Any, Any],
        params: BaseParams,
        state: BaseState,
        factory: DependencyFactory,
        connections: dict[str, BaseResourceManager],
        context: Context,
    ) -> Any:
        """
        Calls an aspect method. All aspects are asynchronous.
        All aspects are required to accept the `log` parameter (sixth).
        Creates a bound logger ActionBoundLogger and passes it.

        The connections parameter is passed to each aspect as the last
        argument, allowing aspects to execute queries through resource
        managers and decide which connections to pass to child actions.

        Args:
            method: aspect method to call.
            action: action instance.
            params: input parameters.
            state: current pipeline state.
            factory: dependency factory.
            connections: dictionary of resource managers.
            context: execution context (used for logging).

        Returns:
            Result of the aspect.
        """
        log = ActionBoundLogger(
            coordinator=self._log_coordinator,
            nest_level=self._nest_level,
            machine_name=self.__class__.__name__,
            mode=self._mode,
            action_name=action.get_full_class_name(),
            aspect_name=method.__name__,
            context=context,
        )
        return await method(action, params, state, factory, connections, log)

    async def _execute_regular_aspects(
        self,
        action: BaseAction[P, R],
        params: P,
        factory: DependencyFactory,
        connections: dict[str, BaseResourceManager],
        context: Context,
    ) -> BaseState:
        """
        Asynchronously executes the chain of regular aspects, calling
        before and after plugin events for each through the coordinator.

        For each aspect:
            - call plugin before-event,
            - execute the aspect itself,
            - check the result through checkers,
            - call plugin after-event with duration.

        The connections parameter is passed through to each aspect.
        """
        action_class = action.__class__
        aspects, _ = self._get_aspects(action_class)
        state = BaseState()

        for method, description in aspects:
            aspect_name = method.__name__

            await self._plugin_coordinator.emit_event(
                event_name=f"before:{aspect_name}",
                action=action,
                params=params,
                state_aspect=state.to_dict(),
                is_summary=method._aspect_type == "summary",
                result=None,
                duration=None,
                factory=factory,
                context=context,
                nest_level=self._nest_level,
            )

            aspect_start = time.time()
            new_state_dict = await self._call_aspect(method, action, params, state, factory, connections, context)
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
                is_summary=method._aspect_type == "summary",
                result=None,
                duration=aspect_duration,
                factory=factory,
                context=context,
                nest_level=self._nest_level,
            )

        return state