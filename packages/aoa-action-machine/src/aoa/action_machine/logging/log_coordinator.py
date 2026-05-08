# packages/aoa-action-machine/src/aoa/action_machine/logging/log_coordinator.py
"""
Central async bus for template resolution and logger fan-out.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``LogCoordinator`` is the only path from ``ScopedLogger`` to concrete loggers.
It validates each message's ``var``, runs ``VariableSubstitutor``, then calls
``handle`` on every registered logger. Senders do not choose recipients.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

``emit`` → validate ``var`` → ``VariableSubstitutor.substitute`` → concurrent
fan-out: optional ANSI strip per logger → ``await logger.handle(...)`` (via
``asyncio.gather(..., return_exceptions=True)``). Failures in individual
``handle`` calls do **not** propagate: every logger is still invoked; errors are
recorded via the **stdlib** ``logging`` package (not via ``LogCoordinator``) to
avoid recursion when the logging pipeline itself breaks.

Substitution pattern ``{%namespace.dotpath}``:

- ``{%var.amount}`` — ``var`` dict (system keys include ``level`` / ``channels``
  as payloads: ``{%var.level.name}``, ``{%var.channels.names}``, or ``.mask`` for
  flags; ``domain``, ``domain_name``; use ``{%var.domain_name}`` for a short domain
  label, not ``repr`` of the class).
- ``{%context.user.user_id}`` — ``context.resolve(...)``.
- ``{%params.card_token}`` — ``params.resolve(...)``.
- ``{%state.total}`` — state key access.
- ``{%scope.action}`` — ``LogScope`` field.

``BaseSchema`` models use ``resolve`` and ``DotPathNavigator``; ``var`` and
``LogScope`` use ``__getitem__`` navigation.

``{iif(...)}`` works in the same template string; strings are quoted inside
``iif``, numbers/booleans are literals.

Flow sketch::

    ScopedLogger._emit(...)
            |
            v
    LogCoordinator.emit(...)
            |
            +--> validate var payloads (level/channels/domain)
            |
            +--> VariableSubstitutor.substitute(...)
            |
            +--> asyncio.gather(logger.handle(...), return_exceptions=True)
                    |
                    +--> per-logger ANSI strip when supports_colors=False
                    +--> isolated failures recorded via stdlib logging

"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from aoa.action_machine.context.context import Context
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.logging.base_logger import BaseLogger
from aoa.action_machine.logging.channel import validate_channels
from aoa.action_machine.logging.level import validate_level
from aoa.action_machine.logging.log_scope import LogScope
from aoa.action_machine.logging.log_var_payloads import LogChannelPayload, LogLevelPayload
from aoa.action_machine.logging.variable_substitutor import VariableSubstitutor
from aoa.action_machine.model.base_params import BaseParams
from aoa.action_machine.model.base_state import BaseState

# Stdlib sink for failures inside ``BaseLogger.handle`` — must not use
# LogCoordinator (no recursive emit). If this logger errors, we drop the line.
_emit_failure_logger = logging.getLogger(__name__)


def _record_logger_handle_failure(logger: BaseLogger, exc: BaseException) -> None:
    """Best-effort stderr logging when a concrete logger breaks during emit."""
    try:
        _emit_failure_logger.error(
            "LogCoordinator: %s (%r) raised during emit; "
            "other loggers were still scheduled. Business await on emit() is not aborted.",
            type(logger).__name__,
            logger,
            exc_info=(type(exc), exc, exc.__traceback__),
        )
    except Exception:
        pass


class LogCoordinator:
    """
AI-CORE-BEGIN
    ROLE: Central logging bus and validation gate.
    CONTRACT: Validate+substitute once, then fan-out to all registered loggers.
    INVARIANTS: Sink failures are isolated and do not abort emit caller flow.
    AI-CORE-END
"""

    def __init__(
        self,
        loggers: list[BaseLogger] | None = None,
    ) -> None:
        """
        Creates a logging coordinator.

        Args:
            loggers: list of BaseLogger instances for initial registration.
                     None or an empty list are allowed.
        """
        self._loggers: list[BaseLogger] = list(loggers) if loggers else []
        self._substitutor: VariableSubstitutor = VariableSubstitutor()

    def add_logger(self, logger: BaseLogger) -> None:
        """
        Registers a new logger with the coordinator.

        The logger is appended to the end of the list – the first registered
        logger is called first.

        Args:
            logger: BaseLogger instance to register.
        """
        self._loggers.append(logger)

    async def emit(
        self,
        message: str,
        var: dict[str, Any],
        scope: LogScope,
        ctx: Context,
        state: BaseState,
        params: BaseParams,
        indent: int,
    ) -> None:
        """
        Main logging method – accepts a message and broadcasts it to all
        registered loggers.

        Performs two steps:

        Step 1: Variable substitution and iif evaluation.
        Delegates all work to VariableSubstitutor.substitute().
        If a variable is not found or iif is invalid, LogTemplateError is raised.

        Step 2: Broadcast.
        Runs ``await logger.handle(...)`` for all loggers concurrently via
        ``asyncio.gather(..., return_exceptions=True)``. Exceptions from any
        ``handle`` are **not** re-raised: each failing logger is recorded via
        stdlib ``logging`` (logger name ``aoa.action_machine.logging.log_coordinator``).
        Empty registration is a no-op.

        Before passing the message to a logger, if the logger does not support
        colors (logger.supports_colors is False), ANSI escape sequences are
        stripped using BaseLogger.strip_ansi_codes.

        Args:
            message: template string with variables {%namespace.path}
                     and/or {iif(...)}.
            var: developer‑supplied variables dictionary.
            scope: current call scope (location in the pipeline).
            ctx: execution context (user, request, environment).
            state: current pipeline state.
            params: action input parameters.
            indent: indentation level (for nested calls).

        Raises:
            LogTemplateError: on any template error.
            ValueError: if var is missing or invalid level/channels.
            TypeError: if ``level``/``channels`` are not payload types, or if
                ``var['domain']`` is not a ``BaseDomain`` subclass type and not ``None``.

        Note:
            Failures inside ``BaseLogger.handle`` do not surface here. Configure
            stdlib handlers on ``aoa.action_machine.logging.log_coordinator``
            if you need alerts for broken sinks.
        """
        if "level" not in var or "channels" not in var:
            raise ValueError("var must contain 'level' and 'channels'")

        lvl = var["level"]
        ch = var["channels"]
        if not isinstance(lvl, LogLevelPayload):
            raise TypeError(
                f"var['level'] must be LogLevelPayload, got {type(lvl).__name__}"
            )
        if not isinstance(ch, LogChannelPayload):
            raise TypeError(
                f"var['channels'] must be LogChannelPayload, got {type(ch).__name__}"
            )

        validate_level(lvl.mask)
        validate_channels(ch.mask)

        raw_domain = var.get("domain")
        if raw_domain is not None:
            if not isinstance(raw_domain, type):
                raise TypeError(
                    f"var['domain'] must be a type or None, "
                    f"got {type(raw_domain).__name__}: {raw_domain!r}"
                )
            if not issubclass(raw_domain, BaseDomain):
                raise TypeError(
                    f"var['domain'] must be a BaseDomain subclass, "
                    f"got {raw_domain.__name__}"
                )

        # Step 1: variable substitution and iif evaluation.
        # LogTemplateError propagates upward if the template is invalid.
        resolved_message = self._substitutor.substitute(
            message, var, scope, ctx, state, params
        )

        # Step 2: broadcast to all loggers (concurrent fan-out for I/O sinks).
        async def _dispatch(logger: BaseLogger) -> None:
            msg_to_send = resolved_message
            if not logger.supports_colors:
                msg_to_send = BaseLogger.strip_ansi_codes(resolved_message)
            await logger.handle(
                scope=scope,
                message=msg_to_send,
                var=var,
                ctx=ctx,
                state=state,
                params=params,
                indent=indent,
            )

        results = await asyncio.gather(
            *(_dispatch(lg) for lg in self._loggers),
            return_exceptions=True,
        )
        for lg, result in zip(self._loggers, results, strict=True):
            if isinstance(result, BaseException):
                _record_logger_handle_failure(lg, result)
