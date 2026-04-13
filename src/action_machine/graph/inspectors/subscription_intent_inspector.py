# src/action_machine/graph/inspectors/subscription_intent_inspector.py
"""
SubscriptionIntentInspector — inspector for plugin ``@on`` subscription metadata.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

For each concrete subclass of ``OnIntent``, scans **declaring** methods on the
class (``vars(target_cls)``), reads ``_on_subscriptions`` scratch written by
``@on``, and builds one ``FacetPayload`` plus a typed ``Snapshot`` per plugin
class. The coordinator stores subscription facets for runtime event routing.

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Source mixin: ``OnIntent``; only classes in that subtree are candidates.
- Entries must be ``SubscriptionInfo`` instances; unknown shapes are skipped.
- Subscription lists are not inherited from base plugin classes — declarations
  live on the class that owns the handler methods (same rule as other facet
  collectors).
- Storage key / facet identity follows the coordinator registration for this
  inspector (aligned with ``subscription_info`` record shape).

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    @on(SomeEvent) async def handler(...)  →  method._on_subscriptions
    SubscriptionIntentInspector.inspect(PluginSubclass)  →  Snapshot, FacetPayload

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

Cross-method validation (event type vs parameter annotation) lives in
``on_intent.validate_subscriptions``; this module focuses on graph emission.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Plugin subscription metadata inspector.
CONTRACT: Aggregate ``_on_subscriptions`` declarations into ``subscription`` facet payloads/snapshots.
INVARIANTS: Candidate roots are ``OnIntent`` subclasses; non-``SubscriptionInfo`` rows are ignored.
FLOW: marker traversal -> declaring-member scan -> subscription row collection -> snapshot -> payload.
FAILURES: Classes without subscriptions return ``None`` payload (skip).
EXTENSION POINTS: Subscription row shape follows ``SubscriptionInfo`` and can evolve with plugin event routing contracts.
AI-CORE-END
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from action_machine.graph.base_facet_snapshot import BaseFacetSnapshot
from action_machine.graph.base_intent_inspector import BaseIntentInspector
from action_machine.graph.payload import FacetPayload
from action_machine.intents.plugins.on_intent import OnIntent
from action_machine.intents.plugins.subscription_info import SubscriptionInfo


class SubscriptionIntentInspector(BaseIntentInspector):
    """
    Inspector that maps ``_on_subscriptions`` into subscription payload entries.

    AI-CORE-BEGIN
    ROLE: Concrete plugin-subscription inspector.
    CONTRACT: Emit ``subscription`` payloads for classes with ``@on`` declarations.
    INVARIANTS: Traversal root is ``OnIntent``; payload edges remain empty.
    AI-CORE-END
    """

    _target_intent: type = OnIntent

    @classmethod
    def _subclasses_recursive(cls) -> list[type]:
        return cls._collect_subclasses(cls._target_intent)

    @classmethod
    def _collect_subscription_entries(cls, target_cls: type) -> tuple[tuple[Any, ...], ...]:
        entries: list[tuple[Any, ...]] = []
        for attr_name, attr_value in vars(target_cls).items():
            func = attr_value.fget if isinstance(attr_value, property) and attr_value.fget else attr_value
            subs_list = getattr(func, "_on_subscriptions", None)
            if subs_list is None:
                continue
            for sub in subs_list:
                if not isinstance(sub, SubscriptionInfo):
                    continue
                entries.append(
                    (
                        attr_name,
                        sub.event_class,
                        sub.action_class,
                        sub.action_name_pattern,
                        sub.aspect_name_pattern,
                        sub.nest_level,
                        sub.domain,
                        sub.predicate,
                        sub.ignore_exceptions,
                        sub.method_name,
                    ),
                )
        return tuple(entries)

    @classmethod
    def _collect_subscriptions(cls, target_cls: type) -> tuple[SubscriptionInfo, ...]:
        subscriptions: list[SubscriptionInfo] = []
        for attr_value in vars(target_cls).values():
            func = attr_value.fget if isinstance(attr_value, property) and attr_value.fget else attr_value
            subs_list = getattr(func, "_on_subscriptions", None)
            if subs_list is None:
                continue
            for sub in subs_list:
                if isinstance(sub, SubscriptionInfo):
                    subscriptions.append(sub)
        return tuple(subscriptions)

    @classmethod
    def _has_subscriptions_invariant(cls, target_cls: type) -> bool:
        return bool(cls._collect_subscription_entries(target_cls))

    @dataclass(frozen=True)
    class Snapshot(BaseFacetSnapshot):
        """Typed plugin subscription facet."""

        class_ref: type
        subscriptions: tuple[SubscriptionInfo, ...]

        def to_facet_payload(self) -> FacetPayload:
            entries = SubscriptionIntentInspector._collect_subscription_entries(
                self.class_ref,
            )
            return FacetPayload(
                node_type="subscription",
                node_name=SubscriptionIntentInspector._make_node_name(self.class_ref),
                node_class=self.class_ref,
                node_meta=SubscriptionIntentInspector._make_meta(subscriptions=entries),
                edges=(),
            )

        @classmethod
        def from_target(
            cls, target_cls: type,
        ) -> SubscriptionIntentInspector.Snapshot:
            return cls(
                class_ref=target_cls,
                subscriptions=SubscriptionIntentInspector._collect_subscriptions(
                    target_cls,
                ),
            )

    @classmethod
    def inspect(cls, target_cls: type) -> FacetPayload | None:
        if not cls._has_subscriptions_invariant(target_cls):
            return None
        return cls._build_payload(target_cls)

    @classmethod
    def facet_snapshot_for_class(
        cls, target_cls: type,
    ) -> SubscriptionIntentInspector.Snapshot | None:
        if not cls._has_subscriptions_invariant(target_cls):
            return None
        return cls.Snapshot.from_target(target_cls)

    @classmethod
    def _build_payload(cls, target_cls: type) -> FacetPayload:
        return cls.Snapshot.from_target(target_cls).to_facet_payload()
