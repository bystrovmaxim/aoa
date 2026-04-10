# src/action_machine/plugins/subscription_gate_host_inspector.py
"""
SubscriptionGateHostInspector — graph inspector for plugin `@on` subscriptions.

The inspector reads method-level `_on_subscriptions` and emits one aggregated
payload per plugin class. Typed data: ``SubscriptionGateHostInspector.Snapshot``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from action_machine.metadata.base_facet_snapshot import BaseFacetSnapshot
from action_machine.metadata.base_gate_host_inspector import BaseGateHostInspector
from action_machine.metadata.payload import FacetPayload
from action_machine.plugins.on_gate_host import OnGateHost
from action_machine.plugins.subscription_info import SubscriptionInfo


class SubscriptionGateHostInspector(BaseGateHostInspector):
    """Inspector that maps `_on_subscriptions` into subscription payload entries."""

    _target_mixin: type = OnGateHost

    @classmethod
    def _subclasses_recursive(cls) -> list[type]:
        return cls._collect_subclasses(cls._target_mixin)

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
            entries = SubscriptionGateHostInspector._collect_subscription_entries(
                self.class_ref,
            )
            return FacetPayload(
                node_type="subscription",
                node_name=SubscriptionGateHostInspector._make_node_name(self.class_ref),
                node_class=self.class_ref,
                node_meta=SubscriptionGateHostInspector._make_meta(subscriptions=entries),
                edges=(),
            )

        @classmethod
        def from_target(
            cls, target_cls: type,
        ) -> SubscriptionGateHostInspector.Snapshot:
            return cls(
                class_ref=target_cls,
                subscriptions=SubscriptionGateHostInspector._collect_subscriptions(
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
    ) -> SubscriptionGateHostInspector.Snapshot | None:
        if not cls._has_subscriptions_invariant(target_cls):
            return None
        return cls.Snapshot.from_target(target_cls)

    @classmethod
    def _build_payload(cls, target_cls: type) -> FacetPayload:
        return cls.Snapshot.from_target(target_cls).to_facet_payload()
