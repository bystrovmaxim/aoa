# packages/aoa-action-machine/src/aoa/action_machine/plugin/core/base_plugin.py
"""
BasePlugin — abstract base class for all ActionMachine plugins.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

BasePlugin is the base class for all plugin implementations. Plugins extend machine
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

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    BasePlugin subclass -> Plugin suffix check
    PluginRunContext -> instance filters -> matching @on handlers

Action filters include descendants of the watched action types. Event filters
include instances of the watched event types. Both default to None, accepting
all events, even when a subclass does not call the base constructor.

"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

from aoa.action_machine.intents.on.on_intent import OnIntent
from aoa.action_machine.naming.suffix import require_suffix
from aoa.action_machine.plugin.core.events import BasePluginEvent
from aoa.action_machine.plugin.core.subscription_info import SubscriptionInfo
from aoa.action_machine.runtime.base_observer import BaseObserver


class BasePlugin(OnIntent, BaseObserver, ABC):
    """
    Initialize per-run state and discover matching lifecycle handlers.

    AI-CORE-BEGIN
    ROLE: Base contract for lifecycle observers.
    CONTRACT: Implement get_initial_state and declare handlers with @on; descendant names end with Plugin.
    INVARIANTS: Per-request state lives in PluginRunContext; optional action/event filters narrow subscriptions.
    AI-CORE-END
    """

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Require the ``Plugin`` suffix for every descendant."""
        super().__init_subclass__(**kwargs)
        require_suffix(cls, "BasePlugin", "Plugin")

    _watch_actions: frozenset[type] | None = None
    _watch_events: frozenset[type] | None = None

    def __init__(
        self,
        *,
        watch_actions: frozenset[type] | None = None,
        watch_events: frozenset[type] | None = None,
    ) -> None:
        """Configure optional action and event subscription filters."""
        self._watch_actions = watch_actions
        self._watch_events = watch_events

    @abstractmethod
    async def get_initial_state(self) -> object:
        """Return initial plugin state for one run invocation."""

    def get_handlers(
        self,
        event: BasePluginEvent,
    ) -> list[tuple[Callable[..., Any], SubscriptionInfo]]:
        """Return handlers matching the event and configured observer filters."""
        if self._watch_actions is not None:
            if not any(issubclass(event.action_class, cls) for cls in self._watch_actions):
                return []
        if self._watch_events is not None:
            if not isinstance(event, tuple(self._watch_events)):
                return []

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
