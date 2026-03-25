"""
Plugin coordinator for ActionMachine.

Separated from ActionProductMachine to divide responsibilities.
ActionProductMachine handles the aspect pipeline,
PluginCoordinator handles the plugin lifecycle:

    1. Lazy initialization of plugin states (get_initial_state).
    2. Caching of handlers by key (event_name, action_name).
    3. Asynchronous execution of handlers (all run concurrently).
    4. Handling of ignore_exceptions – if a handler is marked
       ignore_exceptions=True, its errors are printed but do not
       interrupt the action execution.

The coordinator knows nothing about aspects, roles, connections – only about plugins.
This allows testing plugins separately from the aspect pipeline.

All methods except emit_event are private. The only entry point is
emit_event, called from ActionProductMachine.

Plugin states (_plugin_states) live as long as the coordinator.
On each run() call in ActionProductMachine, the coordinator is reused –
states accumulate across runs. This allows plugins to aggregate metrics
over multiple runs (e.g., a call counter in MetricsPlugin).

The handler cache (_handler_cache) also lives as long as the coordinator.
The cache key is (event_name, action_name). This is safe because
the set of plugin handlers for a given event and action does not change
after plugin creation (the @on decorator is applied at class definition time).

Управление подписками плагинов теперь осуществляется через шлюз OnGate.
Метод _get_handlers использует plugin.get_on_gate().get_handlers() вместо
обхода методов и проверки _plugin_hooks.

Handlers stored in OnGate are unbound methods (from cls.__dict__).
When calling them, the plugin instance must be passed as the first argument (self).

The handler cache now stores tuples (handler, ignore_exceptions, plugin)
to correctly associate each handler with its owning plugin instance,
even when multiple plugin instances share the same class.
"""

import asyncio
from collections.abc import Callable
from typing import Any

from action_machine.Context.context import Context
from action_machine.Core.BaseAction import BaseAction
from action_machine.Core.BaseParams import BaseParams
from action_machine.Core.BaseResult import BaseResult
from action_machine.dependencies.dependency_factory import DependencyFactory
from action_machine.Plugins.Plugin import Plugin
from action_machine.Plugins.PluginEvent import PluginEvent


class PluginCoordinator:
    """
    Coordinator for the plugin lifecycle.

    Manages:
        - Lazy initialization of plugin states (via direct async call).
        - Caching of handlers by (event_name, action_name).
        - Asynchronous execution of handlers (all run concurrently).
        - Handling of ignore_exceptions for individual handlers.

    Knows nothing about aspects, roles, connections – only about plugins.

    Attributes:
        _plugins: list of plugin instances.
        _handler_cache: handler cache by (event_name, action_name).
            Each entry is a list of (handler, ignore_exceptions, plugin) tuples.
        _plugin_states: plugin states dictionary by id(plugin).
    """

    def __init__(
        self,
        plugins: list[Plugin],
    ) -> None:
        """
        Initializes the plugin coordinator.

        Args:
            plugins: list of plugin instances. Order determines
                     the call order of handlers when multiple match.
        """
        self._plugins: list[Plugin] = plugins

        # Handler cache: (event_name, action_name) → [(handler, ignore, plugin)]
        # Populated lazily on first call to _get_handlers for each key.
        # Safe for reuse because the set of handlers does not change after plugin creation.
        self._handler_cache: dict[
            tuple[str, str],
            list[tuple[Callable[..., Any], bool, Plugin]]
        ] = {}

        # Plugin states: id(plugin) → state
        # Initialized lazily on the first event via _init_plugin_states.
        # Updated after each handler call – the handler returns a new state,
        # which is stored back in the dictionary.
        self._plugin_states: dict[int, Any] = {}

    # ---------- Private methods ----------

    def _get_handlers(
        self,
        event_name: str,
        action_name: str,
    ) -> list[tuple[Callable[..., Any], bool, Plugin]]:
        """
        Returns (and caches) the list of handlers for the given event and action.

        On first call for a given (event_name, action_name), iterates through all
        plugins and collects matching handlers via plugin.get_on_gate().get_handlers().
        Each handler is stored together with its owning plugin instance.
        The result is cached for subsequent calls.

        Args:
            event_name: event name (e.g., 'global_start', 'before:validate').
            action_name: full class name of the action (including module).

        Returns:
            List of (handler, ignore_exceptions, plugin) tuples.
            Empty list if no handlers match.
        """
        cache_key = (event_name, action_name)

        if cache_key not in self._handler_cache:
            handlers: list[tuple[Callable[..., Any], bool, Plugin]] = []
            for plugin in self._plugins:
                for handler, ignore in plugin.get_on_gate().get_handlers(event_name, action_name):
                    handlers.append((handler, ignore, plugin))
            self._handler_cache[cache_key] = handlers

        return self._handler_cache[cache_key]

    async def _init_plugin_states(self) -> None:
        """
        Asynchronously initializes the states of all plugins.

        For each plugin whose state has not yet been initialized,
        directly awaits its asynchronous get_initial_state() method.
        This method is idempotent: subsequent calls for already initialized
        plugins do nothing.
        """
        for plugin in self._plugins:
            plugin_id = id(plugin)
            if plugin_id not in self._plugin_states:
                # Directly await the async method – no executor needed.
                state = await plugin.get_initial_state()
                self._plugin_states[plugin_id] = state

    async def _run_single_handler(
        self,
        handler: Callable[..., Any],
        ignore: bool,
        plugin: Plugin,
        event: PluginEvent,
    ) -> None:
        """
        Runs a single plugin handler.

        Retrieves the current state of the plugin from _plugin_states,
        passes it to the handler along with the event,
        and stores the returned new state back.

        The handler is an unbound method from OnGate (stored from cls.__dict__),
        so we must pass the plugin instance as the first argument (self).

        If ignore=True and the handler raises an exception,
        the error is printed to stdout but does not interrupt execution.
        If ignore=False, the exception is propagated upward.

        Args:
            handler: plugin handler method (unbound async def from class).
            ignore: ignore_exceptions flag from the @on decorator.
            plugin: plugin instance (used as self for the handler call).
            event: PluginEvent object with all event data.
        """
        plugin_id = id(plugin)
        state = self._plugin_states[plugin_id]
        try:
            # handler is an unbound method stored by OnGate from cls.__dict__,
            # so we must pass the plugin instance as the first argument (self).
            new_state = await handler(plugin, state, event)
            self._plugin_states[plugin_id] = new_state
        except Exception as e:
            if ignore:
                print(f"Plugin {plugin.__class__.__name__} ignored error: {e}")
            else:
                raise

    def _find_plugin_for_handler(
        self,
        handler: Callable[..., Any],
    ) -> Plugin | None:
        """
        Finds the plugin instance that owns the given handler.

        Since OnGate stores unbound methods (from cls.__dict__), we look up
        the handler by name in the class dict (__dict__) of each plugin's
        class hierarchy.

        Note: When multiple plugin instances share the same class, this method
        returns the FIRST matching instance. For correct per-instance dispatch,
        use _get_handlers() which stores the plugin reference directly.

        This method is kept for backward compatibility with tests that call it
        directly.

        Args:
            handler: plugin handler method (unbound function from class __dict__).

        Returns:
            Plugin instance if found, otherwise None.
        """
        handler_name = getattr(handler, '__name__', None)
        if handler_name is None:
            return None

        for plugin in self._plugins:
            # Walk the MRO to find the method in the class hierarchy
            for cls in type(plugin).__mro__:
                cls_method = cls.__dict__.get(handler_name)
                if cls_method is handler:
                    return plugin

        return None

    # ---------- Public method ----------

    async def emit_event(
        self,
        event_name: str,
        action: BaseAction[Any, Any],
        params: BaseParams,
        state_aspect: dict[str, object] | None,
        is_summary: bool,
        result: BaseResult | None,
        duration: float | None,
        factory: DependencyFactory,
        context: Context,
        nest_level: int,
    ) -> None:
        """
        Dispatches an event to all matching plugin handlers.

        This is the only public method of the coordinator. Called
        from ActionProductMachine at appropriate pipeline points:
        global_start, before:aspect, after:aspect, global_finish.

        Execution sequence:
            1. Obtain the list of handlers from cache (or collect + cache).
            2. If no handlers – early return (optimization).
            3. Initialize plugin states (lazy, idempotent).
            4. Create a PluginEvent object with all data.
            5. Create tasks for each handler and run them concurrently.
            6. Wait for all tasks with asyncio.gather.

        Args:
            event_name: event name (e.g., 'global_start',
                        'before:validate', 'after:save', 'global_finish').
            action: action instance.
            params: action input parameters.
            state_aspect: pipeline state at the event moment
                          (dict or None for global_start/global_finish).
            is_summary: True if the event relates to a summary aspect.
            result: action result (for global_finish, otherwise None).
            duration: execution duration in seconds
                      (for after events and global_finish, otherwise None).
            factory: dependency factory for the current execution.
            context: execution context (user, request, environment).
            nest_level: action call nesting level
                        (0 for root, 1 for child, etc.).
        """
        action_name = action.get_full_class_name()
        handlers = self._get_handlers(event_name, action_name)

        # Optimization: if there are no matching handlers – do nothing.
        # This covers ~80% of events in a typical application.
        if not handlers:
            return

        # Initialize plugin states asynchronously (lazy initialization).
        # Subsequent calls skip already initialized plugins.
        await self._init_plugin_states()

        # Create the event object with all data for handlers.
        event = PluginEvent(
            event_name=event_name,
            action_name=action_name,
            params=params,
            state_aspect=state_aspect,
            is_summary=is_summary,
            deps=factory,
            context=context,
            result=result,
            duration=duration,
            nest_level=nest_level,
        )

        # Collect tasks for all handlers.
        # Each handler already has its plugin reference from _get_handlers.
        tasks: list[Any] = []
        for handler, ignore, plugin in handlers:
            tasks.append(self._run_single_handler(handler, ignore, plugin, event))

        # Run all tasks concurrently.
        # asyncio.gather waits for all tasks to complete.
        # If any handler with ignore=False raises an exception,
        # it will be propagated from gather upward.
        if tasks:
            await asyncio.gather(*tasks)
