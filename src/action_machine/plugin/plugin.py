# src/action_machine/plugin/plugin.py
"""
Plugin — abstract base class for all ActionMachine plugins.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Plugin is the base class for all plugin implementations. Plugins extend machine
behavior without changing core runtime logic (metrics, audit, observability,
side-effect logging, and similar concerns).

Each plugin defines event handlers via ``@on`` and reacts to typed lifecycle
events from ``BasePluginEvent`` hierarchy.

═══════════════════════════════════════════════════════════════════════════════
PLUGIN STATE
═══════════════════════════════════════════════════════════════════════════════

Plugins do NOT keep per-request state in instance attributes.
Per-request state is managed by ``PluginRunContext``:

1. At run start machine calls ``get_initial_state()`` for each plugin.
2. Each handler receives current state and returns updated state.
3. At run end context and states are discarded.

If plugin needs cross-request accumulation, it should use external storage
injected into plugin constructor.

═══════════════════════════════════════════════════════════════════════════════
HANDLER SIGNATURE
═══════════════════════════════════════════════════════════════════════════════

All plugin handlers must follow 4-parameter signature:

    async def handler(self, state, event: EventClass, log) -> state

    - self: plugin instance
    - state: current per-request plugin state
    - event: BasePluginEvent-derived object
    - log: scoped logger bound to plugin scope

Handler must return updated state.

═══════════════════════════════════════════════════════════════════════════════
SUBSCRIPTION VIA EVENT HIERARCHY
═══════════════════════════════════════════════════════════════════════════════

``@on`` takes event class as first argument. Subscription matches that class
and all subclasses via ``isinstance``:

    @on(BasePluginEvent)              - all events
    @on(GlobalLifecycleEvent)         - global_start + global_finish
    @on(GlobalFinishEvent)            - only global_finish
    @on(AspectEvent)                  - all aspect before/after events
    @on(AfterRegularAspectEvent)      - only after regular aspects

Additional filters narrow matches with AND logic inside one subscription.

═══════════════════════════════════════════════════════════════════════════════
HANDLER DISCOVERY
═══════════════════════════════════════════════════════════════════════════════

``get_handlers()`` scans plugin class MRO, finds methods with
``_on_subscriptions``, and returns matching ``SubscriptionInfo`` records with
handler callables. ``PluginRunContext`` calls it on each ``emit_event()``.

"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

from action_machine.intents.on.on_intent import OnIntent
from action_machine.plugin.events import BasePluginEvent
from action_machine.plugin.subscription_info import SubscriptionInfo


class Plugin(OnIntent, ABC):
    """
AI-CORE-BEGIN
    ROLE: Plugin contract for per-run state initialization and handler discovery.
    CONTRACT: Implement get_initial_state and declare handlers via @on.
    INVARIANTS: Per-request state is externalized into PluginRunContext.
    AI-CORE-END
"""

    @abstractmethod
    async def get_initial_state(self) -> object:
        """Return initial plugin state for one run invocation."""

    def get_handlers(
        self,
        event: BasePluginEvent,
    ) -> list[tuple[Callable[..., Any], SubscriptionInfo]]:
        """Return handlers whose event_class prefilter matches incoming event."""
        handlers: list[tuple[Callable[..., Any], SubscriptionInfo]] = []

        for klass in type(self).__mro__:
            if klass is object:
                continue

            for _, attr_value in vars(klass).items():
                subs = getattr(attr_value, "_on_subscriptions", None)
                if subs is None:
                    continue

                for sub in subs:
                    if not isinstance(sub, SubscriptionInfo):
                        continue

                    # Step 1: event_class prefilter via isinstance.
                    if not sub.matches_event_class(event):
                        continue

                    handlers.append((attr_value, sub))

        return handlers
