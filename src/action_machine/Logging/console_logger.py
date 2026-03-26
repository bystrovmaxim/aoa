# ActionMachine/Logging/console_logger.py
"""
Console logger for the AOA logging system.
Outputs messages to the console via print, with support for indentation.

Colors are now applied via template filters (e.g., `{%var.amount|red}`) and are
processed by the logging coordinator. This logger does not add any automatic
coloring or scope prefixes.
"""

from typing import Any

from action_machine.context.context import Context
from action_machine.core.base_params import BaseParams
from action_machine.core.base_state import BaseState
from action_machine.logging.base_logger import BaseLogger
from action_machine.logging.log_scope import LogScope


class ConsoleLogger(BaseLogger):
    """
    Logger that prints messages to the console via print.
    Supports indentation based on the nesting level.

    Colorization is handled by template filters; this logger does not add any
    automatic ANSI codes. It can, however, be configured to strip colors if
    `use_colors=False` (colors are stripped by the coordinator, not here).

    Attributes:
        _use_colors: whether ANSI color codes should be preserved (passed through).
                     If False, the coordinator will strip them before sending.
    """

    def __init__(
        self,
        filters: list[str] | None = None,
        use_colors: bool = True,
    ) -> None:
        """
        Creates a console logger.

        Args:
            filters: list of regex patterns for filtering messages.
                     None or empty list means "accept all".
            use_colors: if True, ANSI color codes are preserved.
                        If False, they will be stripped by the coordinator.
                        Default is True.
        """
        super().__init__(filters=filters)
        self._use_colors: bool = use_colors

    @property
    def supports_colors(self) -> bool:
        """
        Indicates whether this logger preserves ANSI color codes.

        Returns:
            True if `use_colors` is True, otherwise False.
        """
        return self._use_colors

    def _format_line(
        self,
        message: str,
        indent: int,
    ) -> str:
        """
        Formats the final output line.

        Args:
            message: the message string (already with all substitutions and colors).
            indent: indentation level (each level = 2 spaces).

        Returns:
            The formatted line ready for printing.
        """
        indent_str = "  " * indent
        return f"{indent_str}{message}"

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
        Prints the message to the console.

        This method is called only after successful filtering.
        No try/except is used – if print fails, the exception propagates.

        Args:
            scope: current call scope (location in the pipeline).
            message: the fully substituted message (may contain ANSI codes).
            var: developer‑supplied variables.
            ctx: execution context (user, request, environment).
            state: current pipeline state.
            params: action input parameters.
            indent: indentation level (for nested calls).
        """
        line = self._format_line(message, indent)
        print(line)