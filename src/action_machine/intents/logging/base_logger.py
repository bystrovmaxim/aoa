# src/action_machine/intents/logging/base_logger.py
"""
Abstract base class for all loggers in the AOA logging system.

BaseLogger defines a two-phase protocol for message processing:
1. Filtering — ``match_filters`` decides whether this logger should handle
   the message, using optional ``LogSubscription`` rules added via
   ``subscribe``.
2. Writing — the abstract ``write`` method performs the actual output.

With no subscriptions, the logger accepts every message. With one or more
subscriptions, the message is accepted if **any** subscription matches (OR);
within a single subscription, channel, level, and domain conditions are AND.

``var`` is always validated by ``LogCoordinator.emit`` before loggers run
(``level``, ``channels``, ``domain``).

BaseLogger does NOT suppress exceptions from ``write``.

All methods are asynchronous so loggers may perform I/O without blocking
the event loop.

``supports_colors`` and ``strip_ansi_codes`` — see subclass docs.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Abstract logger with optional subscription filtering.
CONTRACT: handle → match_filters then write; subscribe/unsubscribe API.
INVARIANTS: OR across subscriptions; AND inside one LogSubscription; var pre-validated.
FLOW: coordinator → handle → match_filters(var) → write or skip.
FAILURES: write exceptions propagate; subscribe enforces unique keys; subscription
    fields validated in ``LogSubscription.__post_init__``.
EXTENSION POINTS: implement write in subclasses (ConsoleLogger, etc.).
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import Any, Self, overload

from action_machine.domain.base_domain import BaseDomain
from action_machine.intents.context.context import Context
from action_machine.intents.logging.channel import Channel
from action_machine.intents.logging.level import Level
from action_machine.intents.logging.log_scope import LogScope
from action_machine.intents.logging.subscription import LogSubscription
from action_machine.model.base_params import BaseParams
from action_machine.model.base_state import BaseState

# Regular expression to match ANSI escape sequences
_ANSI_ESCAPE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


class BaseLogger(ABC):
    """
    Abstract base logger: optional subscriptions, then ``write``.

    Subclasses implement ``write`` only; ``handle`` runs matching and dispatch.
    """

    def __init__(self) -> None:
        super().__init__()
        self._subscriptions: dict[str, LogSubscription] = {}

    @overload
    def subscribe(
        self,
        key: str,
        *,
        channels: Channel | None = None,
        levels: Level | None = None,
        domains: type[BaseDomain],
    ) -> Self: ...

    @overload
    def subscribe(
        self,
        key: str,
        *,
        channels: Channel | None = None,
        levels: Level | None = None,
        domains: list[type[BaseDomain]],
    ) -> Self: ...

    @overload
    def subscribe(
        self,
        key: str,
        *,
        channels: Channel | None = None,
        levels: Level | None = None,
        domains: tuple[type[BaseDomain], ...],
    ) -> Self: ...

    @overload
    def subscribe(
        self,
        key: str,
        *,
        channels: Channel | None = None,
        levels: Level | None = None,
        domains: None = None,
    ) -> Self: ...

    def subscribe(
        self,
        key: str,
        *,
        channels: Channel | None = None,
        levels: Level | None = None,
        domains: type[BaseDomain]
        | list[type[BaseDomain]]
        | tuple[type[BaseDomain], ...]
        | None = None,
    ) -> Self:
        """
        Add a subscription with a unique key (validated in ``LogSubscription``).

        ``channels`` / ``levels`` / ``domains`` are AND within this rule.
        ``domains`` may be one ``BaseDomain`` subclass, a non-empty list, or a
        non-empty tuple of subclasses. Returns ``self`` for chaining.
        """
        if key in self._subscriptions:
            raise ValueError(f"subscription key '{key}' already exists")

        self._subscriptions[key] = LogSubscription(
            key=key,
            channels=channels,
            levels=levels,
            _domains_raw=domains,
        )
        return self

    def unsubscribe(self, key: str) -> Self:
        """Remove subscription by key. Raises KeyError if missing."""
        if key not in self._subscriptions:
            raise KeyError(f"subscription key '{key}' not found")
        del self._subscriptions[key]
        return self

    @property
    def supports_colors(self) -> bool:
        """Whether this logger preserves ANSI color codes."""
        return False

    @staticmethod
    def strip_ansi_codes(text: str) -> str:
        """Remove ANSI escape sequences from text."""
        return _ANSI_ESCAPE.sub("", text)

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
        No subscriptions → accept all.

        With subscriptions → accept if any subscription matches (OR).
        ``var`` is already validated by the coordinator.
        """
        if not self._subscriptions:
            return True

        for subscription in self._subscriptions.values():
            if subscription.matches(var):
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
        """Run ``match_filters``; if True, call ``write``."""
        matched = await self.match_filters(
            scope, message, var, ctx, state, params, indent,
        )
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
        """Write the message; called only when ``match_filters`` returned True."""
        pass
