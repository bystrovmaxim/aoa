# packages/aoa-action-machine/src/aoa/action_machine/exceptions/event_contract_error.py
"""``EventContractError`` — a typed event, its declaration or its emission breaks a rule."""

from __future__ import annotations


class EventContractError(TypeError):
    """
    AI-CORE-BEGIN
    ROLE: The one error of the typed-event rules.
    CONTRACT: Its message names what was refused and where.
    AI-CORE-END
    """
