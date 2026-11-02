# packages/aoa-action-machine/src/aoa/action_machine/graph/validators/emits_vocabulary_validator.py
"""
EmitsVocabularyValidator — hold every ``@emits`` of a domain to the domain's ``events``.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A domain with ``events`` allows those events and no others, so a method declaring anything
else fails the build. An event that no method declares is allowed. The pass only reads:
no node and no edge change.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from aoa.action_machine.exceptions.event_contract_error import EventContractError
from aoa.action_machine.intents.emits.emits_decorator import EMITS_ATTR
from aoa.action_machine.logging.domain_resolver import resolve_domain
from aoa.action_machine.model.base_action import BaseAction


def _check_action(action_cls: type[Any]) -> None:
    """Refuse an event in this action's ``@emits`` that its domain does not allow."""
    domain = resolve_domain(action_cls)
    if domain is None or not hasattr(domain, "events"):
        return
    for method_name, member in vars(action_cls).items():
        for event in getattr(member, EMITS_ATTR, ()):
            if event not in domain.events:
                raise EventContractError(
                    f"{action_cls.__name__}.{method_name} declares {event.__name__}, "
                    f"which is not in the events of domain '{domain.name}'."
                )


def validate_emits_vocabulary(nodes: Iterable[Any]) -> None:
    """Check every action among ``nodes`` against the vocabulary of its domain."""
    for node in nodes:
        host = node.node_obj
        if isinstance(host, type) and issubclass(host, BaseAction):
            _check_action(host)
