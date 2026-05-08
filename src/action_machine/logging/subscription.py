# src/action_machine/logging/subscription.py
"""
Immutable filter rule for ``BaseLogger.subscribe``.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``LogSubscription`` expresses AND conditions on channel mask, level mask, and
optional domain types. A logger with subscriptions accepts a message if **any**
subscription matches (OR across rules).

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    BaseLogger.subscribe(...)
            |
            v
    LogSubscription.__post_init__()
            |
            +--> validate channels / levels
            +--> normalize domains (single/list/tuple -> tuple|None)
            |
            v
    BaseLogger.match_filters(...)
            |
            v
    subscription.matches(var)
            |
            +--> channel mask intersection
            +--> level mask intersection
            +--> optional domain issubclass check

"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from typing import Any

from action_machine.domain.base_domain import BaseDomain
from action_machine.logging.channel import Channel, validate_channels
from action_machine.logging.level import Level


def _validate_subscription_levels(levels: Level | None) -> None:
    if levels is None:
        return
    if not isinstance(levels, int):
        raise TypeError(f"levels must be Level, got {type(levels).__name__}")
    _all_levels_mask = int(Level.info | Level.warning | Level.critical)
    lv = int(levels)
    if lv == 0:
        raise ValueError("levels cannot be zero")
    if lv & ~_all_levels_mask:
        raise ValueError(f"levels contains unknown bits: {levels}")


def _normalize_subscription_domains(
    domains: type[BaseDomain]
    | list[type[BaseDomain]]
    | tuple[type[BaseDomain], ...]
    | None,
) -> tuple[type[BaseDomain], ...] | None:
    if isinstance(domains, type):
        if not issubclass(domains, BaseDomain):
            raise TypeError(
                f"each domain must be a BaseDomain subclass, got {domains!r}"
            )
        return (domains,)
    if isinstance(domains, list):
        if len(domains) == 0:
            raise ValueError("domains list cannot be empty")
        for d in domains:
            if not isinstance(d, type) or not issubclass(d, BaseDomain):
                raise TypeError(
                    f"each domain must be a BaseDomain subclass, got {d!r}"
                )
        return tuple(domains)
    if isinstance(domains, tuple):
        if len(domains) == 0:
            raise ValueError("domains tuple cannot be empty")
        for d in domains:
            if not isinstance(d, type) or not issubclass(d, BaseDomain):
                raise TypeError(
                    f"each domain must be a BaseDomain subclass, got {d!r}"
                )
        return domains
    return None


@dataclass(frozen=True)
class LogSubscription:
    """
AI-CORE-BEGIN
    ROLE: Immutable per-rule predicate for logger-side filtering.
    CONTRACT: Validate on construction, evaluate channel/level/domain on match.
    INVARIANTS: Rule dimensions are AND-combined inside one subscription.
    AI-CORE-END
"""

    key: str
    channels: Channel | None = None
    levels: Level | None = None
    _domains_raw: InitVar[
        type[BaseDomain]
        | list[type[BaseDomain]]
        | tuple[type[BaseDomain], ...]
        | None
    ] = None
    domains: tuple[type[BaseDomain], ...] | None = field(init=False, default=None)

    def __post_init__(
        self,
        _domains_raw: type[BaseDomain]
        | list[type[BaseDomain]]
        | tuple[type[BaseDomain], ...]
        | None,
    ) -> None:
        if not isinstance(self.key, str) or not self.key.strip():
            raise ValueError("subscription key must be a non-empty string")
        if self.channels is not None:
            validate_channels(self.channels)
        _validate_subscription_levels(self.levels)
        object.__setattr__(self, "domains", _normalize_subscription_domains(_domains_raw))

    def matches(self, var: dict[str, Any]) -> bool:
        """
        True if this subscription accepts ``var``.

        Precondition: ``var`` passed coordinator validation (``level`` /
        ``channels`` are payloads; single level bit; non-zero channels;
        ``domain`` is ``type[BaseDomain]`` or ``None``).
        """
        if self.channels is not None:
            msg_channels = var["channels"].mask
            if (msg_channels & self.channels) == 0:
                return False

        if self.levels is not None:
            msg_level = var["level"].mask
            if (msg_level & self.levels) == 0:
                return False

        if self.domains is not None:
            msg_domain = var.get("domain")
            if msg_domain is None:
                return False
            if not isinstance(msg_domain, type):
                return False
            if not any(issubclass(msg_domain, d) for d in self.domains):
                return False

        return True
