# src/action_machine/logging/console_logger.py
"""
Stdout logger with optional ANSI colors and indent.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``ConsoleLogger`` prints resolved lines via ``print``. Indentation follows the
nested call depth passed as ``indent`` to ``write``. Message filtering uses
``BaseLogger.subscribe`` (channel / level / domain), not constructor flags.

When ``use_colors`` is true and ``var["level"]`` is a ``LogLevelPayload``, the formatted
line (including indent) gets a truecolor **base** foreground for that level.
Explicit colors from templates still apply inside their spans; each full SGR
reset (``\\033[0m``) is followed by the base color again so unstyled segments
stay on the level color, not the terminal default.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    LogCoordinator.emit(...)
            |
            v
    BaseLogger.handle(...)
            |
            v
    ConsoleLogger.write(...)
            |
            +--> _format_line(message, indent)
            |
            +--> colors disabled: strip_ansi_codes -> print
            |
            +--> colors enabled:
                    level payload lookup
                    -> _wrap_line_with_level_base(...)
                    -> print

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

::

    from action_machine.logging import Channel
    from action_machine.logging.console_logger import ConsoleLogger
    from action_machine.logging.log_coordinator import LogCoordinator

    logger = ConsoleLogger()
    logger.subscribe("biz", channels=Channel.business)
    coordinator = LogCoordinator(loggers=[logger])
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from action_machine.context.context import Context
from action_machine.logging.base_logger import BaseLogger
from action_machine.logging.level import Level
from action_machine.logging.log_scope import LogScope
from action_machine.logging.log_var_payloads import LogLevelPayload
from action_machine.model.base_params import BaseParams
from action_machine.model.base_state import BaseState

# Truecolor foreground (24-bit). Reset matches VariableSubstitutor.
_ANSI_RESET: str = "\033[0m"

DEFAULT_LEVEL_FG_PREFIX: dict[Level, str] = {
    Level.info: "\033[38;2;255;255;255m",  # #FFFFFF
    Level.warning: "\033[38;2;255;204;0m",  # #FFCC00
    Level.critical: "\033[38;2;255;34;34m",  # #FF2222
}


class ConsoleLogger(BaseLogger):
    """
AI-CORE-BEGIN
    ROLE: Default interactive sink implementation for logging subsystem.
    CONTRACT: Emit one line per accepted message via ``print``.
    INVARIANTS: Reuses BaseLogger filtering pipeline and subscription rules.
    AI-CORE-END
"""

    def __init__(
        self,
        use_colors: bool = True,
        use_indent: bool = True,
        indent_size: int = 2,
        level_fg_prefixes: Mapping[Level, str] | None = None,
    ) -> None:
        super().__init__()
        self._use_colors: bool = use_colors
        self._use_indent: bool = use_indent
        self._indent_size: int = indent_size
        self._level_fg: dict[Level, str] = dict(DEFAULT_LEVEL_FG_PREFIX)
        if level_fg_prefixes is not None:
            self._level_fg.update(level_fg_prefixes)

    @property
    def supports_colors(self) -> bool:
        return self._use_colors

    def _format_line(self, message: str, indent: int) -> str:
        if self._use_indent:
            indent_str = " " * (indent * self._indent_size)
            return f"{indent_str}{message}"
        return message

    @staticmethod
    def _wrap_line_with_level_base(line: str, base_prefix: str) -> str:
        """
        Prefix the line with base color; after each full reset, re-apply base.

        Expects **real ANSI SGR** (e.g. ``\\033[0m``), not ``__COLOR(...)`` /
        ``__COLOR_END__`` markers — those are expanded in ``VariableSubstitutor``
        before ``LogCoordinator`` calls ``write``.

        Explicit SGR sequences in ``line`` remain in effect until a reset; then
        text returns to the level base, not the terminal default.
        """
        restored = line.replace(_ANSI_RESET, _ANSI_RESET + base_prefix)
        return f"{base_prefix}{restored}{_ANSI_RESET}"

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
        if not self._use_colors:
            message = self.strip_ansi_codes(message)
            line = self._format_line(message, indent)
        else:
            line = self._format_line(message, indent)
            level = var.get("level")
            if isinstance(level, LogLevelPayload) and level.mask in self._level_fg:
                line = self._wrap_line_with_level_base(
                    line, self._level_fg[level.mask],
                )
        print(line)
