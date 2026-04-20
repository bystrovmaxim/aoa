# src/action_machine/legacy/on_intent.py
"""
OnIntent marker mixin for ``@on`` plugin subscriptions.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``OnIntent`` is a marker mixin indicating class support for ``@on`` event
subscriptions. It is used by ``Plugin`` and its subclasses.

Presence of ``OnIntent`` in class MRO documents contract:
"this class may define @on event handler methods".

═══════════════════════════════════════════════════════════════════════════════
TYPE-SAFE SUBSCRIPTION
═══════════════════════════════════════════════════════════════════════════════

``@on`` takes an event class from ``BasePluginEvent`` hierarchy as first
argument. Subscription matches the declared class and its subclasses via
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
    from action_machine.logging.channel import Channel

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


class OnIntent:
    """
AI-CORE-BEGIN
    ROLE: Marker contract for plugin event subscriptions.
    CONTRACT: Classes with @on subscriptions must carry this marker.
    INVARIANTS: Logic-free mixin for ``issubclass`` / MRO checks.
    AI-CORE-END
"""

    pass
