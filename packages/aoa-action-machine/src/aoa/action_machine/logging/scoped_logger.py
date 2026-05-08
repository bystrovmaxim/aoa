# packages/aoa-action-machine/src/aoa/action_machine/logging/scoped_logger.py
"""
Scoped logger bound to aspect or plugin execution coordinates.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``ScopedLogger`` is the API aspects and plugins use to emit log lines. It
injects system fields into ``var`` and forwards a single ``emit`` to
``LogCoordinator`` per call.

═══════════════════════════════════════════════════════════════════════════════
GLOSSARY (SHORT)
═══════════════════════════════════════════════════════════════════════════════

- **Log line** — one event: template text plus structured ``var``.
- **var** — dict of fields attached to the line (user kwargs + system keys).
- **Channel** — what the event is about (``IntFlag``); required on every call.
- **Level** — urgency (``IntFlag``); exactly one bit per message, from method name.
- **Domain** — ``type[BaseDomain] | None`` from the caller at construction;
  ``ScopedLogger`` does not read ``@meta``.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    await box.info(Channel.debug, "SQL took {%var.ms}ms", ms=42)
         │
         ▼
    ScopedLogger._emit(Level.info, channels, message, **kwargs)
         │  no reserved keys in kwargs
         │  var = kwargs + LogLevelPayload + LogChannelPayload + domain + domain_name
         ▼
    LogCoordinator.emit(...)  — validates var, substitutes, fans out

Aspect scope: ``action``, ``aspect``, ``nest_level``.
Plugin scope: ``plugin``, ``action``, ``event``, ``nest_level``.

Templates: ``{%var.*}``, ``{%state.*}``, ``{%params.*}``, ``{%context.*}``,
``{%scope.*}``, ``{iif(...)}``. Use ``{%var.level.name}`` / ``{%var.channels.names}``
for display; ``{%var.level.mask}`` / ``{%var.channels.mask}`` are IntFlags if needed.
Prefer ``{%var.domain_name}`` for domain text; ``{%var.domain}`` is the type object.

"""

from typing import Any

from aoa.action_machine.context.context import Context
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.logging.channel import Channel, channel_mask_label, validate_channels
from aoa.action_machine.logging.domain_resolver import domain_label
from aoa.action_machine.logging.level import Level, level_label, validate_level
from aoa.action_machine.logging.log_coordinator import LogCoordinator
from aoa.action_machine.logging.log_scope import LogScope
from aoa.action_machine.logging.log_var_payloads import (
    LogChannelPayload,
    LogLevelPayload,
)
from aoa.action_machine.model.base_params import BaseParams
from aoa.action_machine.model.base_state import BaseState

_RESERVED_KEYS = frozenset({"level", "channels", "domain", "domain_name"})


class ScopedLogger:
    """
    AI-CORE-BEGIN
    ROLE: Scope-bound facade that prepares var payloads for coordinator emit.
    CONTRACT: Map info/warning/critical calls to one validated emit each.
    INVARIANTS: Reserved system keys are owned by logger, not user kwargs.
    AI-CORE-END
"""

    def __init__(
        self,
        coordinator: LogCoordinator,
        nest_level: int,
        action_name: str,
        aspect_name: str,
        context: Context,
        state: BaseState | None = None,
        params: BaseParams | None = None,
        plugin_name: str | None = None,
        event_name: str | None = None,
        *,
        domain: type[BaseDomain] | None = None,
    ) -> None:
        self._coordinator = coordinator
        self._nest_level = nest_level
        self._context = context
        self._state = state if state is not None else BaseState()
        self._params = params if params is not None else BaseParams()
        self._domain = domain
        self._domain_name = domain_label(domain)

        if plugin_name is not None:
            self._scope = LogScope(
                plugin=plugin_name,
                action=action_name,
                event=event_name or "",
                nest_level=nest_level,
            )
        else:
            self._scope = LogScope(
                action=action_name,
                aspect=aspect_name,
                nest_level=nest_level,
            )

    async def _emit(
        self,
        log_level: Level,
        channels: Channel,
        message: str,
        **kwargs: Any,
    ) -> None:
        conflict = _RESERVED_KEYS & kwargs.keys()
        if conflict:
            raise ValueError(
                f"Reserved keys {conflict} cannot be passed in kwargs. "
                f"They are set automatically by the logging system."
            )

        validate_channels(channels)
        validate_level(log_level)

        var = dict(kwargs)
        var["level"] = LogLevelPayload(mask=log_level, name=level_label(log_level))
        var["channels"] = LogChannelPayload(
            mask=channels, names=channel_mask_label(channels),
        )
        var["domain"] = self._domain
        var["domain_name"] = self._domain_name

        await self._coordinator.emit(
            message=message,
            var=var,
            scope=self._scope,
            ctx=self._context,
            state=self._state,
            params=self._params,
            indent=self._nest_level,
        )

    async def info(
        self, channels: Channel, message: str, **kwargs: Any,
    ) -> None:
        await self._emit(Level.info, channels, message, **kwargs)

    async def warning(
        self, channels: Channel, message: str, **kwargs: Any,
    ) -> None:
        await self._emit(Level.warning, channels, message, **kwargs)

    async def critical(
        self, channels: Channel, message: str, **kwargs: Any,
    ) -> None:
        await self._emit(Level.critical, channels, message, **kwargs)
