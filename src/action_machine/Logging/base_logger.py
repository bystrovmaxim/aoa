# src/action_machine/logging/base_logger.py
"""
Abstract base class for all loggers in the AOA logging system.
BaseLogger defines a two‑phase protocol for message processing:
1. Filtering – the match_filters method quickly determines whether
   this logger should process the message.
2. Writing – the abstract write method is implemented by descendants
   and performs the actual output (console, file, ELK, etc.).

Filtering is based on regular expressions. Each logger receives a list
of filters at creation time. Filters are compiled in __init__ for
performance (they are not recompiled on every call).

The filter string is built from scope.as_dotpath() and serialized var
keys – this allows filtering by any combination of conditions.

If the filter list is empty, the logger accepts all messages (no filters
means “accept everything”). If at least one filter matches, the message
is accepted. If none match, the message is discarded.

BaseLogger does NOT suppress exceptions. If the write method fails,
the exception propagates up the stack. This is a conscious decision:
a broken logger should be discovered immediately, not a month later
when logs are needed.

All methods are asynchronous – loggers may perform I/O (file writes,
network sends) without blocking the event loop.

New in 0.0.5:
- `supports_colors` property to indicate whether the logger can handle
  ANSI color codes.
- `strip_ansi_codes` static method to remove ANSI sequences from a string.
"""

import re
from abc import ABC, abstractmethod
from typing import Any

from action_machine.context.context import Context
from action_machine.core.base_params import BaseParams
from action_machine.core.base_state import BaseState
from action_machine.logging.log_scope import LogScope

# Regular expression to match ANSI escape sequences
_ANSI_ESCAPE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')


class BaseLogger(ABC):
    """
    Abstract base class for all loggers.
    Defines the message processing protocol: filtering via regular expressions,
    then writing via the abstract write method.
    Descendants only need to implement write – filtering and the call to write
    are handled by the base class through the handle method.
    Exceptions from write are not suppressed – if a logger is broken,
    the system must know about it immediately.
    """

    def __init__(self, filters: list[str] | None = None) -> None:
        """
        Initializes the logger with a set of filters.

        Filters are strings containing regular expressions, compiled at
        instance creation for performance. Each filter is applied using
        re.search (not fullmatch), allowing matches anywhere in the context string.

        If filters is empty or None, filtering is disabled – the logger accepts
        all messages.

        Args:
            filters: list of regex strings for filtering.
                     Each string is compiled into a re.Pattern.
                     None or empty list means "accept all".
        """
        self._filters: list[re.Pattern[str]] = [re.compile(f) for f in (filters or [])]

    @property
    def supports_colors(self) -> bool:
        """
        Indicates whether this logger can handle ANSI color codes.

        Returns:
            True if the logger preserves ANSI codes, False if they should be stripped.
            Base implementation returns False; descendants may override.
        """
        return False

    @staticmethod
    def strip_ansi_codes(text: str) -> str:
        """
        Removes ANSI escape sequences from a string.

        Args:
            text: input string possibly containing ANSI codes.

        Returns:
            String with all ANSI sequences removed.
        """
        return _ANSI_ESCAPE.sub('', text)

    def _build_filter_string(
        self,
        scope: LogScope,
        message: str,
        var: dict[str, Any],
    ) -> str:
        """
        Builds the context string for filter matching.

        The string is composed of three parts:
        1. scope.as_dotpath() – location in the pipeline.
        2. The message text.
        3. Serialized var keys and values as "key=value".

        Parts are joined by spaces. This allows filtering by any combination:
        by action name, by message text, by variable values.

        Args:
            scope: current call scope.
            message: already substituted message text.
            var: dictionary of variables passed to the log call.

        Returns:
            A single string for regex matching.
        """
        parts: list[str] = []
        dotpath = scope.as_dotpath()
        if dotpath:
            parts.append(dotpath)
        if message:
            parts.append(message)
        for key, value in var.items():
            parts.append(f"{key}={value}")
        return " ".join(parts)

    async def match_filters(
        self,
        scope: LogScope,
        message: str,
        var: dict[str, Any],
        ctx: Context,
        state: BaseState,
        params: BaseParams,
        indent: int,
    ) -> bool:
        """
        Checks whether this logger should process the message.

        Filtering logic:
        1. If the filter list is empty, return True (no filters – accept all).
        2. Build the filter string via _build_filter_string.
        3. Apply each compiled re.Pattern using search.
        4. As soon as one filter matches, return True.
        5. If none match, return False.

        The method is asynchronous for interface uniformity, although the
        current implementation does not perform I/O.

        Args:
            scope: current call scope.
            message: substituted message text.
            var: developer‑supplied variables.
            ctx: execution context (user, request, environment).
            state: current pipeline state.
            params: action input parameters.
            indent: indentation level (for nested calls).

        Returns:
            True if the message passed filtering and should be written,
            False if it is rejected by all filters.
        """
        if not self._filters:
            return True
        filter_string = self._build_filter_string(scope, message, var)
        for pattern in self._filters:
            if pattern.search(filter_string):
                return True
        return False

    async def handle(
        self,
        scope: LogScope,
        message: str,
        var: dict[str, Any],
        ctx: Context,
        state: BaseState,
        params: BaseParams,
        indent: int,
    ) -> None:
        """
        Entry point for processing a message by the logger.

        Called by LogCoordinator in a loop for each registered logger.
        Performs two phases:
        1. Filtering – calls match_filters. If False, exits without further action.
        2. Writing – calls the abstract write method.

        No try/except – if write fails, the exception propagates upward.

        Args:
            scope: current call scope.
            message: substituted message text.
            var: developer‑supplied variables.
            ctx: execution context.
            state: current pipeline state.
            params: action input parameters.
            indent: indentation level.
        """
        matched = await self.match_filters(scope, message, var, ctx, state, params, indent)
        if not matched:
            return
        await self.write(scope, message, var, ctx, state, params, indent)

    @abstractmethod
    async def write(
        self,
        scope: LogScope,
        message: str,
        var: dict[str, Any],
        ctx: Context,
        state: BaseState,
        params: BaseParams,
        indent: int,
    ) -> None:
        """
        Writes the message to the specific output channel.

        Abstract method – implemented by each concrete logger.
        Called only if match_filters returned True.
        Must NOT suppress exceptions.

        Args:
            scope: current call scope.
            message: substituted message text.
            var: developer‑supplied variables.
            ctx: execution context.
            state: current pipeline state.
            params: action input parameters.
            indent: indentation level.
        """
        pass
