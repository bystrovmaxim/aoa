# src/action_machine/intents/plugins/on_intent.py
"""
OnIntent marker mixin and subscription annotation validators.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``OnIntent`` is a marker mixin indicating class support for ``@on`` event
subscriptions. It is used by ``Plugin`` and its subclasses.

Presence of ``OnIntent`` in class MRO documents contract:
"this class may define @on event handler methods".

During metadata build, if class has methods with ``_on_subscriptions``, class
must inherit ``OnIntent``; otherwise validation raises ``TypeError``.

═══════════════════════════════════════════════════════════════════════════════
TYPE-SAFE SUBSCRIPTION
═══════════════════════════════════════════════════════════════════════════════

``@on`` takes an event class from ``BasePluginEvent`` hierarchy as first
argument. Subscription matches the declared class and subclasses via
``isinstance`` in ``PluginRunContext``.

Additional filters (action_class, action_name_pattern, aspect_name_pattern,
nest_level, domain, predicate) apply AND-logic inside one subscription.
OR-logic is achieved by multiple ``@on`` decorators on one method.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    class Plugin(OnIntent):           <- intent: @on grammar on methods
        async def get_initial_state(self) -> Any:
            ...

    class CounterPlugin(Plugin):

        async def get_initial_state(self) -> dict:
            return {}

        @on(GlobalFinishEvent, ignore_exceptions=False)
        async def on_count_call(self, state, event: GlobalFinishEvent, log):
            state[event.action_name] = state.get(event.action_name, 0) + 1
            return state

    # @on decorator writes into method:
    #   method._on_subscriptions = [SubscriptionInfo(
    #       event_class=GlobalFinishEvent,
    #       method_name="on_count_call",
    #       ignore_exceptions=False,
    #   )]

    # MetadataBuilder collects subscriptions for validation;
    # plugin @on handlers are not materialized as graph ``subscription`` facets.

    # MetadataBuilder -> require_*_intent_marker + validate_subscriptions
    # checks: has subscriptions -> issubclass(cls, OnIntent).

    # PluginRunContext.emit_event(event):
    #   plugin.get_handlers(event) -> candidate handlers by isinstance
    #   _matches_all_filters(event, sub) -> filter checks
    #   handler(plugin, state, event, log) -> call

═══════════════════════════════════════════════════════════════════════════════
INTENT CONSISTENCY
═══════════════════════════════════════════════════════════════════════════════

All ActionMachine intent markers follow the same pattern: empty logic-free
classes used by ``issubclass`` checks in decorators and graph build. ``OnIntent``
aligns with other markers such as ``CheckRolesIntent``, ``AspectIntent``,
``CheckerIntent``, ``ActionMetaIntent``, ``ConnectionIntent``, ``OnErrorIntent``,
``ContextRequiresIntent``, and ``DescribedFieldsIntent``.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    # Plugin already inherits OnIntent, so any plugin supports @on:
    from action_machine.intents.logging.channel import Channel

    class MetricsPlugin(Plugin):
        async def get_initial_state(self) -> dict:
            return {"total": 0, "errors": 0}

        @on(GlobalFinishEvent)
        async def on_track_total(self, state, event: GlobalFinishEvent, log):
            state["total"] += 1
            return state

        @on(UnhandledErrorEvent)
        async def on_track_errors(self, state, event: UnhandledErrorEvent, log):
            state["errors"] += 1
            return state

        @on(AfterRegularAspectEvent, aspect_name_pattern=r"validate_.*")
        async def on_validation_done(self, state, event: AfterRegularAspectEvent, log):
            await log.info(
                Channel.debug,
                "Validation finished: {%var.name}",
                name=event.aspect_name,
            )
            return state
"""

from __future__ import annotations

import inspect
from typing import Any

from action_machine.intents.plugins.events import BasePluginEvent
from action_machine.intents.plugins.subscription_info import SubscriptionInfo


class OnIntent:
    """
    Marker mixin denoting support for ``@on`` decorator.

    Classes inheriting ``OnIntent`` may declare ``@on`` methods subscribed to
    typed ActionMachine plugin events.

    AI-CORE-BEGIN
    ROLE: Marker contract for plugin event subscriptions.
    CONTRACT: Classes with @on subscriptions must carry this marker.
    INVARIANTS: Logic-free mixin used by metadata validators.
    AI-CORE-END
    """

    pass


def require_on_intent_marker(cls: type, subscriptions: list[Any]) -> None:
    """If class declares @on subscriptions, it must inherit OnIntent."""
    if subscriptions and not issubclass(cls, OnIntent):
        event_classes = ", ".join(
            s.event_class.__name__ if isinstance(s, SubscriptionInfo) else str(s)
            for s in subscriptions
        )
        raise TypeError(
            f"Class {cls.__name__} declares event subscriptions ({event_classes}) "
            f"but does not inherit OnIntent. @on subscription grammar requires "
            f"OnIntent in MRO. Use Plugin or add OnIntent to inheritance chain."
        )


def _extract_event_annotation(cls: type, method_name: str) -> type | None:
    func = None
    for klass in cls.__mro__:
        if method_name in vars(klass):
            func = vars(klass)[method_name]
            break

    if func is None:
        return None

    try:
        sig = inspect.signature(func)
    except (ValueError, TypeError):
        return None

    params_list = list(sig.parameters.values())

    if len(params_list) < 3:
        return None

    event_param = params_list[2]
    annotation = event_param.annotation
    if annotation is inspect.Parameter.empty:
        return None

    if isinstance(annotation, type) and issubclass(annotation, BasePluginEvent):
        return annotation

    return None


def validate_subscriptions(
    cls: type,
    subscriptions: list[SubscriptionInfo],
) -> None:
    """Validate compatibility of @on event_class with handler event annotation."""
    for sub in subscriptions:
        if not isinstance(sub, SubscriptionInfo):
            continue

        annotation = _extract_event_annotation(cls, sub.method_name)
        if annotation is None:
            continue

        if not issubclass(sub.event_class, annotation):
            raise TypeError(
                f"Class {cls.__name__}: method '{sub.method_name}' is subscribed "
                f"to {sub.event_class.__name__} via @on, but event parameter "
                f"is annotated as {annotation.__name__}. "
                f"{sub.event_class.__name__} is not a subclass of "
                f"{annotation.__name__}, so handler may receive event without "
                f"expected fields. Change annotation to "
                f"{sub.event_class.__name__} or a more general type "
                f"(for example, BasePluginEvent)."
            )
