"""
Base class for all ActionMachine plugins.
Handlers receive a single argument event: PluginEvent.
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any


class Plugin(ABC):
    """
    Abstract base class for all plugins.

    Each plugin must implement the asynchronous method ``get_initial_state``,
    which returns the initial state for one action run. The state will be
    passed to all plugin handlers, and each handler must return the updated state.

    Plugins should not store state in instance attributes, as it must be isolated
    for each ``run`` call. Instead, the state is managed by the machine and
    passed via the ``state_plugin`` parameter to each handler.

    Handler methods are marked with the ``@on`` decorator from the ``Decorators`` module.
    They must be asynchronous (defined with ``async def``), even if they do not contain
    ``await``, because the machine calls them with ``await``.
    """

    @abstractmethod
    async def get_initial_state(self) -> object:
        """
        Returns the initial state of the plugin for a single action execution.

        This method is called by the machine before the first execution of any handler
        of this plugin within the current ``run`` call. The return value can be of any
        type (usually a dictionary or a custom object). It will be passed to all handlers
        as the first argument ``state_plugin``, and each handler must return the new state.

        Returns:
            Initial state for this run.
        """
        ...

    def get_handlers(self, event_name: str, class_name: str) -> list[tuple[Callable[..., Any], bool]]:
        """
        Returns a list of matching handlers for the given event and action class.

        This method iterates over all instance methods, looks for those marked with the
        ``@on`` decorator, and checks whether the regular expressions from the subscriptions
        match the given ``event_name`` and ``class_name``. If a match is found, the method
        is added to the result together with the ``ignore_exceptions`` flag from the corresponding
        subscription.

        Args:
            event_name: event name (e.g., 'before:choose_channel').
            class_name: full class name of the action (including module).

        Returns:
            List of (handler method, ignore_exceptions) tuples for all matching subscriptions.
        """
        handlers: list[tuple[Callable[..., Any], bool]] = []
        for method_name in dir(self):
            method = getattr(self, method_name)
            if not callable(method) or not hasattr(method, "_plugin_hooks"):
                continue
            for event_regex, class_regex, ignore_exceptions in method._plugin_hooks:
                if event_regex.fullmatch(event_name) and class_regex.fullmatch(class_name):
                    handlers.append((method, ignore_exceptions))
                    break
        return handlers