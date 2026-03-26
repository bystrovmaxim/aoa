# ActionMachine/Logging/action_bound_logger.py
"""
Logger bound to the current aspect.

Automatically adds execution coordinates to LogScope:
- machine: machine class name (e.g., "ActionProductMachine")
- mode: execution mode (e.g., "test", "production")
- action: full action class name (including module)
- aspect: aspect method name

The logging level is passed in var under the key "level".
User data is passed only through kwargs and ends up in var.
"""

from typing import Any

from action_machine.context.context import Context
from action_machine.core.base_params import BaseParams
from action_machine.core.base_state import BaseState
from action_machine.logging.log_coordinator import LogCoordinator
from action_machine.logging.log_scope import LogScope


class ActionBoundLogger:
    """
    Logger bound to the current aspect.

    Created by ActionProductMachine for each aspect call.
    All aspects are required to accept the `log` parameter (sixth).

    The info, warning, error, debug methods send a message through LogCoordinator,
    automatically adding the `level` key and user kwargs to var.
    """

    def __init__(
        self,
        coordinator: LogCoordinator,
        nest_level: int,
        machine_name: str,
        mode: str,
        action_name: str,
        aspect_name: str,
        context: Context,
    ) -> None:
        """
        Initialize the bound logger.

        Args:
            coordinator: logging coordinator (bus).
            nest_level: action call nesting level.
            machine_name: machine class name (e.g., "ActionProductMachine").
            mode: execution mode (e.g., "test", "production").
            action_name: full action class name (including module).
            aspect_name: aspect method name.
            context: execution context (user, request, environment).
        """
        self._coordinator = coordinator
        self._nest_level = nest_level
        self._machine_name = machine_name
        self._mode = mode
        self._action_name = action_name
        self._aspect_name = aspect_name
        self._context = context

        # Create a scope with a fixed key order.
        # Order: machine, mode, action, aspect.
        self._scope = LogScope(
            machine=machine_name,
            mode=mode,
            action=action_name,
            aspect=aspect_name,
        )

    async def _emit(self, lvl: str, message: str, **kwargs: Any) -> None:
        """
        Internal method to send a message.

        Args:
            lvl: logging level (info, warning, error, debug).
            message: message text (may contain {%...} and {iif(...)} templates).
            **kwargs: user data that will end up in var.
        """
        # Remove the key 'level' from kwargs if the user accidentally passed it.
        # We use the system level, so the user's level is ignored.
        kwargs.pop("level", None)

        # Put only the level and user data into var.
        var = {"level": lvl, **kwargs}

        await self._coordinator.emit(
            message=message,
            var=var,
            scope=self._scope,
            ctx=self._context,
            state=BaseState(),      # state is not passed automatically
            params=BaseParams(),    # params are not passed automatically
            indent=self._nest_level,
        )

    async def info(self, message: str, **kwargs: Any) -> None:
        """
        Send an INFO level message.

        Args:
            message: message text.
            **kwargs: user data.
        """
        await self._emit("info", message, **kwargs)

    async def warning(self, message: str, **kwargs: Any) -> None:
        """
        Send a WARNING level message.

        Args:
            message: message text.
            **kwargs: user data.
        """
        await self._emit("warning", message, **kwargs)

    async def error(self, message: str, **kwargs: Any) -> None:
        """
        Send an ERROR level message.

        Args:
            message: message text.
            **kwargs: user data.
        """
        await self._emit("error", message, **kwargs)

    async def debug(self, message: str, **kwargs: Any) -> None:
        """
        Send a DEBUG level message.

        Args:
            message: message text.
            **kwargs: user data.
        """
        await self._emit("debug", message, **kwargs)