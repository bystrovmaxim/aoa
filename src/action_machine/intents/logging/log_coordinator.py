# src/action_machine/intents/logging/log_coordinator.py
"""
Central async bus for template resolution and logger fan-out.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``LogCoordinator`` is the only path from ``ScopedLogger`` to concrete loggers.
It validates each message's ``var``, runs ``VariableSubstitutor``, then calls
``handle`` on every registered logger. Senders do not choose recipients.

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- One ``emit`` per user log call. ``var`` must include ``level`` and ``channels``.
- ``level`` is a ``LogLevelPayload``; ``.mask`` is exactly one info/warning/critical bit.
- ``channels`` is a ``LogChannelPayload``; ``.mask`` is a non-zero allowed channel mask.
- ``domain`` is ``None`` or a ``type[BaseDomain]`` (validated in ``emit``).
  ``ScopedLogger`` also sets ``domain_name`` for human-readable templates; it is
  not separately type-checked by the coordinator.
- Per-logger filtering uses ``BaseLogger.match_filters`` (subscriptions), not
  the coordinator.

═══════════════════════════════════════════════════════════════════════════════
DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

``emit`` → validate ``var`` → ``VariableSubstitutor.substitute`` → concurrent
fan-out: optional ANSI strip per logger → ``await logger.handle(...)`` (via
``asyncio.gather``).

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

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Register loggers at construction or via ``add_logger``. Each logger may call
``subscribe`` to restrict traffic.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- Missing variables, bad ``iif``, unknown namespace → ``LogTemplateError``.
- Invalid ``var`` → ``ValueError`` / ``TypeError`` before substitution.
- Logger failures are not caught by the coordinator.

All entry points are async so I/O loggers do not block the event loop.

Color: template filters (e.g. ``{%var.amount|red}``) and ``iif`` color helpers;
if ``logger.supports_colors`` is false, ``BaseLogger.strip_ansi_codes`` runs.

Sensitive data: see ``VariableSubstitutor`` / ``@sensitive``.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Logging bus + var gate + substitution orchestration.
CONTRACT: emit(message, var, scope, ctx, state, params, indent) validates then broadcasts.
INVARIANTS: var level/channels/domain rules always enforced; no regex filters here.
FLOW: validate var → substitute → strip ANSI per logger → handle (parallel gather).
FAILURES: LogTemplateError, ValueError, TypeError; logger exceptions propagate.
EXTENSION POINTS: add_logger; custom BaseLogger implementations.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

import asyncio
from typing import Any

from action_machine.domain.base_domain import BaseDomain
from action_machine.intents.context.context import Context
from action_machine.intents.logging.base_logger import BaseLogger
from action_machine.intents.logging.channel import validate_channels
from action_machine.intents.logging.level import validate_level
from action_machine.intents.logging.log_scope import LogScope
from action_machine.intents.logging.log_var_payloads import LogChannelPayload, LogLevelPayload
from action_machine.intents.logging.variable_substitutor import VariableSubstitutor
from action_machine.model.base_params import BaseParams
from action_machine.model.base_state import BaseState


class LogCoordinator:
    """
    Async coordinator: validate ``var``, substitute templates, fan out to loggers.

    Registration: constructor ``loggers`` or ``add_logger``. Filtering is
    per-logger via ``subscribe`` inside ``match_filters``, not here.
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
        ``asyncio.gather`` (empty registration is a no-op).
        No try/except – the first raised exception propagates (others may still
        be running briefly; see :func:`asyncio.gather`).

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

        await asyncio.gather(*(_dispatch(lg) for lg in self._loggers))
