# packages/aoa-action-machine/src/aoa/action_machine/intents/access_control/allowed_verdict.py
"""Yes."""

from __future__ import annotations

from pydantic import Field

from aoa.action_machine.intents.access_control.base_verdict import BaseVerdict


class AllowedVerdict(BaseVerdict):
    """Yes, go ahead. Carries no reason at all: there is nothing to explain when nothing
    objected. This is what an action answers unless it says otherwise."""

    kind: str = Field(default="AllowedVerdict", min_length=1)
