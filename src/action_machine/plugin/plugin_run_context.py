# src/action_machine/plugin/plugin_run_context.py
"""
PluginRunContext — isolated plugin context for one run invocation.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

PluginRunContext encapsulates all mutable plugin state needed for one
``ActionProductMachine.run()`` call. Each run creates its own context that
exists only for that run lifecycle and is then discarded.

This guarantees per-request isolation: plugin states from one run never affect
another run, including concurrent execution in the same event loop.

═══════════════════════════════════════════════════════════════════════════════
TYPE-SAFE EVENT DELIVERY
═══════════════════════════════════════════════════════════════════════════════

``emit_event()`` takes one event object from ``BasePluginEvent`` hierarchy.
Machine emits concrete event objects at pipeline checkpoints and passes them
into this method, where matching handlers are resolved and invoked.

═══════════════════════════════════════════════════════════════════════════════
FILTER CHAIN DURING EVENT EMISSION
═══════════════════════════════════════════════════════════════════════════════

When ``emit_event()`` receives event, it traverses subscriptions across all
plugins. Filters are checked from cheapest to most expensive with early exit.

    Event enters emit_event()
             │
             ▼
    Step 1: isinstance(event, sub.event_class)?
             │  Cheap type check.
             │  NO -> skip handler
             │
             ▼
    Step 2: action_class filter -> isinstance(action, sub.action_class)?
             │  NO -> skip
             │
             ▼
    Step 3: action_name_pattern -> re.search(...)
             │  NO -> skip
             │
             ▼
    Step 4: aspect_name_pattern -> re.search(...)
             │  Only for AspectEvent subclasses.
             │  NO -> skip
             │
             ▼
    Step 5: nest_level filter
             │  NO -> skip
             │
             ▼
    Step 6: domain filter via metadata coordinator snapshot
             │  NO -> skip
             │
             ▼
    Step 7: predicate(event)?
             │  Most expensive user-defined check.
             │  NO -> skip
             │
             ▼
    ALL FILTERS PASSED -> call handler

Step 1 happens in ``Plugin.get_handlers()``, steps 2-7 in
``PluginRunContext._matches_all_filters()``.

═══════════════════════════════════════════════════════════════════════════════
AND LOGIC INSIDE ONE @on
═══════════════════════════════════════════════════════════════════════════════

All filters in one subscription are AND-combined. Unspecified filters are
skipped. OR-logic is achieved by declaring multiple ``@on`` subscriptions on
the same method.

═══════════════════════════════════════════════════════════════════════════════
DOMAIN FILTERING
═══════════════════════════════════════════════════════════════════════════════

Domain filter uses GraphCoordinator snapshot lookup for event action class and
is evaluated late (step 6) after cheap checks.

═══════════════════════════════════════════════════════════════════════════════
PREDICATE AND EVENT TYPING
═══════════════════════════════════════════════════════════════════════════════

``predicate`` is user-defined filter callable. Runtime event type is guaranteed
to conform to subscribed ``event_class`` because predicate runs only after step 1
``isinstance`` check.

    @on(GlobalFinishEvent, predicate=lambda e: e.duration_ms > 1000)
    # e is GlobalFinishEvent at runtime, duration_ms access is safe

═══════════════════════════════════════════════════════════════════════════════
HANDLER EXECUTION STRATEGY
═══════════════════════════════════════════════════════════════════════════════

After filtering, matched handlers are executed using one of two strategies
chosen by ``ignore_exceptions`` flags:

1. All handlers have ``ignore_exceptions=True``:
   Run in parallel via ``asyncio.gather(return_exceptions=True)``. Failures are
   suppressed and optionally logged.

2. At least one handler has ``ignore_exceptions=False``:
   Run sequentially. Failure in critical handler is re-raised and stops chain.

═══════════════════════════════════════════════════════════════════════════════
HANDLER LOGGER
═══════════════════════════════════════════════════════════════════════════════

Every plugin handler receives ``ScopedLogger`` as ``log`` parameter.
Context builds logger per call with scope fields and
``domain=resolve_domain(event.action_class)``.

Scope fields are available in templates via ``{%scope.*}``:
    from action_machine.logging.channel import Channel

    await log.info(
        Channel.debug,
        "[{%scope.plugin}] Action {%scope.action} completed",
    )

Creating scoped logger requires ``log_coordinator``, ``machine_name``, and
``mode`` passed from machine into ``emit_event()``.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE
═══════════════════════════════════════════════════════════════════════════════

    ActionProductMachine._run_internal(...)
        │
        │  event = GlobalStartEvent(action_class=..., ...)
        │  await plugin_ctx.emit_event(event, coordinator=..., ...)
        ▼
    PluginRunContext.emit_event(event, ...)
        │
        │  For each plugin:
        │    handlers = plugin.get_handlers(event)  <- Step 1: event_class
        │    For each (handler, sub):
        │      _matches_all_filters(event, sub)     <- Steps 2-7
        │      -> collect matched
        │
        │  Choose execution strategy:
        │    all ignore=True -> parallel
        │    otherwise -> sequential
        │
        │  For each matched handler:
        │    create ScopedLogger
        │    state = await handler(plugin, state, event, log)
        │    update _plugin_states[id(plugin)]
        ▼

═══════════════════════════════════════════════════════════════════════════════
EXAMPLE USAGE
═══════════════════════════════════════════════════════════════════════════════

    # In ActionProductMachine:
    event = GlobalFinishEvent(
        action_class=type(action),
        action_name=action.get_full_class_name(),
        nest_level=current_nest,
        context=context,
        params=params,
        result=result,
        duration_ms=total_duration * 1000,
    )
    await plugin_ctx.emit_event(
        event,
        log_coordinator=self._log_coordinator,
        machine_name=self.__class__.__name__,
        mode=self._mode,
        coordinator=self._coordinator,
    )
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

from action_machine.logging.channel import Channel
from action_machine.logging.domain_resolver import resolve_domain
from action_machine.logging.log_coordinator import LogCoordinator
from action_machine.logging.scoped_logger import ScopedLogger
from action_machine.plugin.events import BasePluginEvent
from action_machine.plugin.plugin import Plugin
from action_machine.plugin.subscription_info import SubscriptionInfo
from action_machine.model.base_params import BaseParams
from action_machine.model.base_state import BaseState


class PluginRunContext:
    """
    Isolated plugin context for one run invocation.

    Created by ``PluginCoordinator.create_run_context()`` and used to route
    typed events through subscription filters while maintaining per-run plugin
    states.

    AI-CORE-BEGIN
    ROLE: Runtime dispatcher and state holder for plugin handlers.
    CONTRACT: Filter subscriptions and execute matched handlers per strategy.
    INVARIANTS: State is isolated per run and keyed by plugin instance id.
    AI-CORE-END
    """

    def __init__(
        self,
        plugins: list[Plugin],
        initial_states: dict[int, Any],
    ) -> None:
        """Initialize run context with plugin list and initial states."""
        self._plugins: list[Plugin] = plugins
        self._plugin_states: dict[int, Any] = dict(initial_states)

    # ─────────────────────────────────────────────────────────────────────
    # Subscription filtering (steps 2-7)
    # ─────────────────────────────────────────────────────────────────────

    @staticmethod
    def _matches_all_filters(  # pylint: disable=too-many-return-statements
        event: BasePluginEvent,
        sub: SubscriptionInfo,
        coordinator: Any | None = None,
    ) -> bool:
        """Check remaining subscription filters after event_class prefilter."""
        # Step 2: action_class
        if sub.action_class is not None:
            if not isinstance(event.action_class, type):
                return False
            # Event action class must match configured class tuple.
            if not issubclass(event.action_class, sub.action_class):
                return False

        # Step 3: action_name_pattern
        if not sub.matches_action_name(event.action_name):
            return False

        # Step 4: aspect_name_pattern
        if not sub.matches_aspect_name(event):
            return False

        # Step 5: nest_level
        if not sub.matches_nest_level(event.nest_level):
            return False

        # Step 6: domain
        if sub.domain is not None and coordinator is not None:
            try:
                m = coordinator.get_snapshot(event.action_class, "meta")
                action_domain = m.domain if m is not None else None
                if action_domain is not sub.domain:
                    return False
            except Exception:
                return False

        # Step 7: predicate
        if not sub.matches_predicate(event):
            return False

        return True

    # ─────────────────────────────────────────────────────────────────────
    # Collect matched handlers
    # ─────────────────────────────────────────────────────────────────────

    def _collect_matched_handlers(
        self,
        event: BasePluginEvent,
        coordinator: Any | None = None,
    ) -> list[tuple[Plugin, Callable[..., Any], SubscriptionInfo]]:
        """Collect all handlers that pass full filter chain."""
        matched: list[tuple[Plugin, Callable[..., Any], SubscriptionInfo]] = []

        for plugin in self._plugins:
            candidates = plugin.get_handlers(event)

            for handler, sub in candidates:
                if self._matches_all_filters(event, sub, coordinator):
                    matched.append((plugin, handler, sub))

        return matched

    # ─────────────────────────────────────────────────────────────────────
    # Create ScopedLogger for plugin handler
    # ─────────────────────────────────────────────────────────────────────

    @staticmethod
    def _create_plugin_logger(
        log_coordinator: LogCoordinator | None,
        machine_name: str,
        mode: str,
        plugin: Plugin,
        event: BasePluginEvent,
    ) -> ScopedLogger | None:
        """Create per-handler ScopedLogger or return None if logging disabled."""
        if log_coordinator is None:
            return None

        return ScopedLogger(
            coordinator=log_coordinator,
            nest_level=event.nest_level,
            machine_name=machine_name,
            mode=mode,
            action_name=event.action_name,
            aspect_name="",
            context=event.context,
            state=BaseState(),
            params=event.params if isinstance(event.params, BaseParams) else BaseParams(),
            plugin_name=type(plugin).__name__,
            event_name=type(event).__name__,
            domain=resolve_domain(event.action_class),
        )

    @staticmethod
    async def _log_suppressed_handler_exception(
        exc: Exception,
        log: ScopedLogger | None,
        method_name: str,
    ) -> None:
        if log is None:
            return
        await log.critical(
            Channel.error,
            "Plugin handler {%var.handler_name} failed and was suppressed "
            "(ignore_exceptions=True): {%var.exc_type}: {%var.exc_message}",
            handler_name=method_name,
            exc_type=type(exc).__name__,
            exc_message=str(exc),
        )

    # ─────────────────────────────────────────────────────────────────────
    # Execute one handler
    # ─────────────────────────────────────────────────────────────────────

    async def _run_single_handler(
        self,
        plugin: Plugin,
        handler: Callable[..., Any],
        event: BasePluginEvent,
        log: ScopedLogger | None,
    ) -> None:
        """Run one plugin handler and persist updated per-run state."""
        plugin_id = id(plugin)
        state = self._plugin_states.get(plugin_id)

        new_state = await handler(plugin, state, event, log)

        self._plugin_states[plugin_id] = new_state

    # ─────────────────────────────────────────────────────────────────────
    # Execution strategies: parallel vs sequential
    # ─────────────────────────────────────────────────────────────────────

    async def _run_parallel(
        self,
        matched: list[tuple[Plugin, Callable[..., Any], SubscriptionInfo]],
        event: BasePluginEvent,
        log_coordinator: LogCoordinator | None,
        machine_name: str,
        mode: str,
    ) -> None:
        """Run handlers in parallel when all ignore exceptions."""
        tasks = []
        for plugin, handler, _sub in matched:
            log = self._create_plugin_logger(
                log_coordinator, machine_name, mode, plugin, event,
            )
            tasks.append(
                self._run_single_handler(plugin, handler, event, log)
            )

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for (plugin, _handler, sub), result in zip(matched, results, strict=True):
                if isinstance(result, Exception):
                    log = self._create_plugin_logger(
                        log_coordinator, machine_name, mode, plugin, event,
                    )
                    await self._log_suppressed_handler_exception(
                        result, log, sub.method_name,
                    )

    async def _run_sequential(
        self,
        matched: list[tuple[Plugin, Callable[..., Any], SubscriptionInfo]],
        event: BasePluginEvent,
        log_coordinator: LogCoordinator | None,
        machine_name: str,
        mode: str,
    ) -> None:
        """Run handlers sequentially when any subscription is critical."""
        for plugin, handler, sub in matched:
            log = self._create_plugin_logger(
                log_coordinator, machine_name, mode, plugin, event,
            )
            try:
                await self._run_single_handler(plugin, handler, event, log)
            except Exception as exc:
                if not sub.ignore_exceptions:
                    raise
                await self._log_suppressed_handler_exception(
                    exc, log, sub.method_name,
                )

    # ─────────────────────────────────────────────────────────────────────
    # Main method: emit_event
    # ─────────────────────────────────────────────────────────────────────

    async def emit_event(
        self,
        event: BasePluginEvent,
        *,
        log_coordinator: LogCoordinator | None = None,
        machine_name: str = "",
        mode: str = "",
        coordinator: Any | None = None,
    ) -> None:
        """Deliver typed event to all handlers that pass filter chain."""
        # Collect handlers that passed all filters.
        matched = self._collect_matched_handlers(event, coordinator)

        if not matched:
            return

        # Choose execution strategy.
        all_ignore = all(sub.ignore_exceptions for _, _, sub in matched)

        if all_ignore:
            await self._run_parallel(
                matched, event, log_coordinator, machine_name, mode,
            )
        else:
            await self._run_sequential(
                matched, event, log_coordinator, machine_name, mode,
            )

    # ─────────────────────────────────────────────────────────────────────
    # Access plugin state (tests/introspection)
    # ─────────────────────────────────────────────────────────────────────

    def get_plugin_state(self, plugin: Plugin) -> Any:
        """Return current per-run plugin state (primarily for tests)."""
        return self._plugin_states[id(plugin)]
