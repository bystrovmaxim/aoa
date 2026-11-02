# packages/aoa-action-machine/src/aoa/action_machine/runtime/emission_rules.py
"""
Emission rules — what one method may write, checked before a line goes out.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A method's ``box`` carries these rules only when a switch is on. Plugins and the machine
write without a ``box`` of a method, so the rules cover operation code and nothing else.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    method_box / TestBench
        └── emission_rules_for(action_cls, method_name)  → EmissionRules or None
                └── ToolsBox(emission=...)
                        └── box.info(...) → rules.check(event) → logger

"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, NoReturn

from aoa.action_machine.exceptions.event_contract_error import EventContractError
from aoa.action_machine.intents.emits.emits_decorator import EMITS_ATTR
from aoa.action_machine.logging.domain_resolver import resolve_domain
from aoa.action_machine.model.base_event import BaseEvent


@dataclass(frozen=True, slots=True)
class EmissionRules:
    """
    AI-CORE-BEGIN
    ROLE: What one method of an action may write.
    CONTRACT: ``check`` passes a permitted line and raises for any other.
    FAILURES: :exc:`EventContractError` naming the action, the method and what was refused.
    AI-CORE-END
    """

    action_name: str
    method_name: str
    declared: tuple[type[BaseEvent], ...] | None
    vocabulary: tuple[type[Any], ...] | None
    domain_name: str | None

    def check(self, event: BaseEvent | None) -> None:
        """Refuse a line this method may not write."""
        if event is None:
            self._refuse("a line with no event: it is a typed zone")
        name = type(event).__name__
        if self.vocabulary is not None and type(event) not in self.vocabulary:
            self._refuse(f"{name}: it is not in the events of domain '{self.domain_name}'")
        if self.declared is None or type(event) not in self.declared:
            self._refuse(f"{name}: it is not in the method's @emits")

    def _refuse(self, what: str) -> NoReturn:
        """Raise the refusal, naming who wrote what."""
        raise EventContractError(f"{self.action_name}.{self.method_name} may not write {what}.")


def emission_rules_for(action_cls: type, method_name: str) -> EmissionRules | None:
    """Return the rules of one method, or ``None`` when no switch is on."""
    declared = getattr(getattr(action_cls, method_name, None), EMITS_ATTR, None)
    domain = resolve_domain(action_cls)
    vocabulary = getattr(domain, "events", None)
    if declared is None and vocabulary is None:
        return None
    return EmissionRules(action_cls.__name__, method_name, declared, vocabulary, getattr(domain, "name", None))
