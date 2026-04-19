# src/action_machine/legacy/subscription_intent_inspector.py
"""
SubscriptionIntentInspector — plugin ``@on`` metadata (no graph facets).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``@on`` handlers are a **runtime** concern: ``Plugin.get_handlers`` /
``PluginRunContext`` read ``_on_subscriptions`` on methods. They are **not**
materialized as interchange ``subscription`` vertices on the static coordinator
graph.

This class remains a :class:`~graph.base_intent_inspector.BaseIntentInspector`
subclass for API symmetry and optional tooling; :meth:`inspect` and
:meth:`facet_snapshot_for_class` always return ``None`` so
:class:`~graph.graph_coordinator.GraphCoordinator` never commits
handler subscription rows.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Placeholder / tooling hook for plugin subscription metadata (graph-disabled).
CONTRACT: Do not emit ``subscription`` facet payloads or snapshots for ``OnIntent`` handlers.
INVARIANTS: Candidate roots would be ``OnIntent`` subclasses; graph path is a no-op.
FLOW: ``inspect`` / ``facet_snapshot_for_class`` → ``None``; ``_build_payload`` satisfies ABC only.
AI-CORE-END
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from action_machine.legacy.on_intent import OnIntent
from action_machine.plugin.subscription_info import SubscriptionInfo
from graph.base_facet_snapshot import BaseFacetSnapshot
from graph.base_intent_inspector import BaseIntentInspector
from graph.facet_vertex import FacetVertex


class SubscriptionIntentInspector(BaseIntentInspector):
    """
    Plugin ``@on`` metadata — **not** projected into the coordinator graph.

    AI-CORE-BEGIN
    ROLE: No-op graph inspector for handler subscriptions.
    CONTRACT: ``inspect`` / ``facet_snapshot_for_class`` return ``None``.
    INVARIANTS: Traversal root is ``OnIntent`` when registered; default coordinator omits registration.
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

    @dataclass(frozen=True)
    class Snapshot(BaseFacetSnapshot):
        """Typed plugin subscription facet (not stored by default coordinator)."""

        class_ref: type
        subscriptions: tuple[SubscriptionInfo, ...]

        def to_facet_vertex(self) -> FacetVertex:
            entries = SubscriptionIntentInspector._collect_subscription_entries(
                self.class_ref,
            )
            return FacetVertex(
                node_type="subscription",
                node_name=SubscriptionIntentInspector._make_host_dependent_node_name(
                    self.class_ref, "subscriptions",
                ),
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
    def inspect(cls, _target_cls: type) -> FacetVertex | None:
        return None

    @classmethod
    def facet_snapshot_for_class(
        cls, _target_cls: type,
    ) -> SubscriptionIntentInspector.Snapshot | None:
        return None

    @classmethod
    def _build_payload(cls, target_cls: type) -> FacetVertex:
        return cls.Snapshot.from_target(target_cls).to_facet_vertex()
