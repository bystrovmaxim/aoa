# src/action_machine/logging/log_coordinator.py
"""
Log coordinator for the AOA logging system.

LogCoordinator is the single logging bus to which any number of independent
loggers can be attached. Aspects and plugins send messages to the coordinator
without knowing about the specific recipients.

The coordinator delegates variable substitution to the VariableSubstitutor class
and broadcasts the result to all attached loggers.

Variable substitution uses the pattern {%namespace.dotpath}, where namespace
determines the data source:

- {%var.amount} – looks in the developer‑supplied var dictionary.
- {%context.user.user_id} – calls context.resolve("user.user_id").
- {%params.card_token} – calls params.resolve("card_token").
- {%state.total} – accesses state by key "total".
- {%scope.action} – looks up scope by key "action".

For objects inheriting BaseSchema (Context, UserInfo, RequestInfo, RuntimeInfo,
BaseParams, BaseResult), the resolve method is used, which traverses nested
objects via dot‑separated keys through the unified DotPathNavigator. For plain
dictionaries (var) and LogScope, the same navigator handles traversal
transparently via duck-typed __getitem__ access.

Unified variable syntax:
The {%namespace.dotpath} pattern works EVERYWHERE – both in the message text
and inside {iif(...)}. Inside iif, string values are automatically quoted,
while numbers and booleans are inserted as literals.

Strict error policy:
- If a variable is not found – LogTemplateError is raised.
- If an iif expression is invalid – LogTemplateError is raised.
- If the namespace is unknown – LogTemplateError is raised.

An error in a log template is a developer bug and must be detected immediately
on the first run.

LogCoordinator does NOT suppress exceptions from loggers. If a logger is broken,
the exception propagates up the stack.

All methods are asynchronous – the coordinator and loggers may perform I/O
(file writes, network sends) without blocking the event loop.

Color support: messages may contain ANSI color codes via template filters
(e.g., `{%var.amount|red}`) and color functions inside iif (e.g., `red('text')`).
Before sending to a logger, the coordinator checks `logger.supports_colors`.
If False, ANSI codes are stripped using `BaseLogger.strip_ansi_codes`.

Sensitive data masking: handled by VariableSubstitutor; see its documentation.
"""

from typing import Any

from action_machine.context.context import Context
from action_machine.core.base_params import BaseParams
from action_machine.core.base_state import BaseState
from action_machine.logging.base_logger import BaseLogger
from action_machine.logging.log_scope import LogScope
from action_machine.logging.variable_substitutor import VariableSubstitutor


class LogCoordinator:
    """
    Unified logging bus for AOA.

    Accepts messages via the emit method, delegates variable substitution to
    VariableSubstitutor, and broadcasts the result to all registered loggers.

    Loggers are registered at creation via the loggers parameter, or later via
    add_logger.

    The coordinator does not filter messages – filtering is done independently
    by each logger in its match_filters method.

    Strict error policy: any template error immediately raises LogTemplateError.

    Attributes:
        _loggers: list of registered loggers.
        _substitutor: VariableSubstitutor instance for variable substitution
                      and iif evaluation.
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
        Calls await logger.handle(...) for each logger.
        No try/except – any error propagates immediately.

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
        """
        # Step 1: variable substitution and iif evaluation.
        # LogTemplateError propagates upward if the template is invalid.
        resolved_message = self._substitutor.substitute(
            message, var, scope, ctx, state, params
        )

        # Step 2: broadcast to all loggers
        for logger in self._loggers:
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
