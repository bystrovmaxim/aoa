# packages/aoa-action-machine/src/aoa/action_machine/model/base_event.py
"""
BaseEvent — a recorded business fact, and the typed variables of its log line.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

An event says what became true. It takes the place of ``kwargs`` in a call of ``box``,
after the text of the line, and a logger receives it as ``var``. The system fields of a
line belong to ``box``: the author leaves them empty, and a dump of the fact omits them.

Import ``BaseEvent`` from this module. The ``model`` package does not export it, because
this module needs the logging package, and the logging package needs ``Context``, which
itself imports the ``model`` package.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    OrderCompletedEvent(order_id="o1")          the author's event, system fields empty
         │
         ▼
    box.info(Channel.business, "text", event)
         │
         ▼
    ScopedLogger.emit_event(...)                a copy with the system fields filled
         │
         ▼
    LogCoordinator.emit(var=copy)               a logger reads it by key, like any ``var``

"""

from __future__ import annotations

import inspect
from typing import Any

from pydantic import ConfigDict, Field, model_validator

from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.domain.event_marker import EventMarker
from aoa.action_machine.exceptions.event_contract_error import EventContractError
from aoa.action_machine.exceptions.naming_suffix_error import NamingSuffixError
from aoa.action_machine.logging.log_var_payloads import LogChannelPayload, LogLevelPayload
from aoa.action_machine.model.base_schema import BaseSchema

_REQUIRED_SUFFIX = "Event"

SYSTEM_FIELDS = frozenset({"level", "channels", "domain", "domain_name"})

# A logger reads an event through these methods, so a field must not take their place.
_READ_METHODS = frozenset({"get", "keys", "values", "items", "resolve"})


class BaseEvent(EventMarker, BaseSchema):
    """
    AI-CORE-BEGIN
    ROLE: A recorded business fact, the tenth primitive.
    CONTRACT: Immutable, extra fields forbidden; a subclass ends with ``Event``.
    INVARIANTS: Only ``box`` fills the system fields, and only in a copy.
    FAILURES: :exc:`EventContractError` for a reserved field name; ``ValidationError`` when an author sets a system field.
    AI-CORE-END
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    level: LogLevelPayload | None = Field(default=None, exclude=True)
    channels: LogChannelPayload | None = Field(default=None, exclude=True)
    domain: type[BaseDomain] | None = Field(default=None, exclude=True)
    domain_name: str | None = Field(default=None, exclude=True)

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Refuse a name without the suffix, and a field with a reserved name."""
        super().__init_subclass__(**kwargs)
        if not cls.__name__.endswith(_REQUIRED_SUFFIX):
            raise NamingSuffixError(
                f"Class '{cls.__name__}' inherits from BaseEvent but its name must end with "
                f"'{_REQUIRED_SUFFIX}'. Rename it to '{cls.__name__}{_REQUIRED_SUFFIX}'."
            )
        reserved = (SYSTEM_FIELDS | _READ_METHODS) & inspect.get_annotations(cls).keys()
        if reserved:
            raise EventContractError(
                f"Event '{cls.__name__}' declares reserved field names {sorted(reserved)}. Rename them."
            )

    @model_validator(mode="before")
    @classmethod
    def _refuse_system_fields(cls, data: Any) -> Any:
        """Refuse a system field set by the author."""
        if isinstance(data, dict):
            named = SYSTEM_FIELDS & data.keys()
            if named:
                raise ValueError(f"System fields belong to box and cannot be set: {sorted(named)}.")
        return data
