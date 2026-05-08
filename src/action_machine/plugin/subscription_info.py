# src/action_machine/plugin/subscription_info.py
"""
SubscriptionInfo — frozen dataclass for one plugin subscription configuration.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

SubscriptionInfo stores full configuration of one plugin method subscription.
It is created by ``@on`` at class definition time and stored on the handler as
``_on_subscriptions``. :class:`~action_machine.plugin.plugin.Plugin` gathers
those records while resolving handlers for a run; :class:`~action_machine.plugin.plugin_run_context.PluginRunContext`
consumes ``SubscriptionInfo`` when matching emitted events.

One plugin method may have multiple subscriptions (multiple ``@on``). OR logic
applies across subscriptions for one method; AND logic applies inside a single
subscription where all configured filters must pass.

═══════════════════════════════════════════════════════════════════════════════
FILTERS AND SEMANTICS
═══════════════════════════════════════════════════════════════════════════════

Each filter is optional. ``None`` means "no filtering by this criterion".
Filters are checked sequentially in ``PluginRunContext`` from cheap to
expensive with early exit on first mismatch.

Filter check order:

    1. event_class        — isinstance(event, event_class)
    2. action_class       — isinstance(action, action_class)
    3. action_name_pattern — re.search(pattern, event.action_name)
    4. aspect_name_pattern — re.search(pattern, event.aspect_name)
    5. nest_level         — event.nest_level in nest_level
    6. domain             — ``coordinator.get_snapshot(action_class, "meta").domain`` is domain
    7. predicate          — predicate(event)

═══════════════════════════════════════════════════════════════════════════════
REGEX COMPILATION
═══════════════════════════════════════════════════════════════════════════════

``action_name_pattern`` and ``aspect_name_pattern`` store raw regex strings.
Compiled patterns are cached in private fields during ``__post_init__`` via
``object.__setattr__`` (frozen bypass). This ensures one-time compilation and
fast matching during runtime checks.

Invalid regex is detected in ``__post_init__`` and raises ``ValueError`` at
class definition time (when ``@on`` is applied), not during first request.

═══════════════════════════════════════════════════════════════════════════════
nest_level NORMALIZATION
═══════════════════════════════════════════════════════════════════════════════

``nest_level`` normalization in ``__post_init__``:
    - ``None`` -> ``None`` (no filtering)
    - ``int`` -> ``tuple[int]``
    - ``tuple[int, ...]`` -> unchanged

This simplifies runtime check to ``event.nest_level in sub.nest_level``.

═══════════════════════════════════════════════════════════════════════════════
aspect_name_pattern VALIDATION
═══════════════════════════════════════════════════════════════════════════════

``aspect_name_pattern`` applies only to ``AspectEvent`` subclasses (events
with ``aspect_name``). If provided for a non-aspect event class, configuration
is invalid and ``__post_init__`` raises ``ValueError``.

═══════════════════════════════════════════════════════════════════════════════
CREATION EXAMPLE (via @on decorator)
═══════════════════════════════════════════════════════════════════════════════

    # @on decorator creates SubscriptionInfo:
    sub = SubscriptionInfo(
        event_class=GlobalFinishEvent,
        action_class=(CreateOrderAction,),
        action_name_pattern=r"orders\\..*",
        aspect_name_pattern=None,
        nest_level=(0,),
        domain=OrdersDomain,
        predicate=lambda e: e.duration_ms > 1000,
        ignore_exceptions=True,
        method_name="on_slow_order_finish",
    )
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, cast

from action_machine.plugin.events import AspectEvent, BasePluginEvent


@dataclass(frozen=True)
class SubscriptionInfo:
    """
    Frozen dataclass describing one plugin event subscription.
    """

    # Required fields
    event_class: type[BasePluginEvent]
    method_name: str

    # Filters (optional, None means no filtering)
    action_class: tuple[type, ...] | None = None
    action_name_pattern: str | None = None
    aspect_name_pattern: str | None = None
    nest_level: tuple[int, ...] | None = None
    domain: type | None = None
    predicate: Callable[[BasePluginEvent], bool] | None = None

    # Error handling behavior
    ignore_exceptions: bool = True

    # Validation and caching

    def __post_init__(self) -> None:
        """Validate config and cache compiled regexes."""
        # 1. event_class validation
        if not isinstance(self.event_class, type) or not issubclass(
            self.event_class, BasePluginEvent
        ):
            raise TypeError(
                f"SubscriptionInfo: event_class must be a BasePluginEvent "
                f"subclass, got {self.event_class!r}."
            )

        # 2. aspect_name_pattern applicability validation
        if self.aspect_name_pattern is not None:
            if not issubclass(self.event_class, AspectEvent):
                raise ValueError(
                    f"SubscriptionInfo: aspect_name_pattern is set, but "
                    f"event_class={self.event_class.__name__} is not an "
                    f"AspectEvent subclass. aspect_name_pattern is only valid "
                    f"for AspectEvent descendants."
                )

        # 3. nest_level normalization
        raw_nest = self.nest_level
        if isinstance(raw_nest, int):
            object.__setattr__(self, "nest_level", (raw_nest,))

        # 4. action_name_pattern compilation
        compiled_action: re.Pattern[str] | None = None
        if self.action_name_pattern is not None:
            try:
                compiled_action = re.compile(self.action_name_pattern)
            except re.error as exc:
                raise ValueError(
                    f"SubscriptionInfo: invalid regex in action_name_pattern: "
                    f"{self.action_name_pattern!r}. Error: {exc}"
                ) from exc
        object.__setattr__(self, "_compiled_action_name_pattern", compiled_action)

        # 5. aspect_name_pattern compilation
        compiled_aspect: re.Pattern[str] | None = None
        if self.aspect_name_pattern is not None:
            try:
                compiled_aspect = re.compile(self.aspect_name_pattern)
            except re.error as exc:
                raise ValueError(
                    f"SubscriptionInfo: invalid regex in aspect_name_pattern: "
                    f"{self.aspect_name_pattern!r}. Error: {exc}"
                ) from exc
        object.__setattr__(self, "_compiled_aspect_name_pattern", compiled_aspect)

    # Computed properties

    @property
    def compiled_action_name_pattern(self) -> re.Pattern[str] | None:
        """Compiled regex for action_name_pattern."""
        return cast(
            re.Pattern[str] | None,
            object.__getattribute__(self, "_compiled_action_name_pattern"),
        )

    @property
    def compiled_aspect_name_pattern(self) -> re.Pattern[str] | None:
        """Compiled regex for aspect_name_pattern."""
        return cast(
            re.Pattern[str] | None,
            object.__getattribute__(self, "_compiled_aspect_name_pattern"),
        )

    # Filter match methods

    def matches_event_class(self, event: BasePluginEvent) -> bool:
        """Check event class match via isinstance."""
        return isinstance(event, self.event_class)

    def matches_action_class(self, action: Any) -> bool:
        """Check action type filter via isinstance."""
        if self.action_class is None:
            return True
        return isinstance(action, self.action_class)

    def matches_action_name(self, action_name: str) -> bool:
        """Check action_name against compiled regex filter."""
        pattern = object.__getattribute__(self, "_compiled_action_name_pattern")
        if pattern is None:
            return True
        return pattern.search(action_name) is not None

    def matches_aspect_name(self, event: BasePluginEvent) -> bool:
        """Check aspect_name against compiled regex filter when applicable."""
        pattern = object.__getattribute__(self, "_compiled_aspect_name_pattern")
        if pattern is None:
            return True
        if not isinstance(event, AspectEvent):
            return True
        return pattern.search(event.aspect_name) is not None

    def matches_nest_level(self, event_nest_level: int) -> bool:
        """Check nest level filter."""
        if self.nest_level is None:
            return True
        return event_nest_level in self.nest_level

    def matches_predicate(self, event: BasePluginEvent) -> bool:
        """Check optional user predicate."""
        if self.predicate is None:
            return True
        return self.predicate(event)
