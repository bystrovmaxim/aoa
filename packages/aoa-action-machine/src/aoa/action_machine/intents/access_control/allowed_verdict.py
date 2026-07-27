# packages/aoa-action-machine/src/aoa/action_machine/intents/access_control/allowed_verdict.py
"""Yes."""

from __future__ import annotations

from typing import Any

from aoa.action_machine.intents.access_control.base_verdict import BaseVerdict


class AllowedVerdict(BaseVerdict):
    """Yes, go ahead. Carries no reason at all: there is nothing to explain when nothing
    objected. This is what an action answers unless it says otherwise."""

    def __init__(self, kind: str = "AllowedVerdict", **kwargs: Any) -> None:
        super().__init__(kind=kind, **kwargs)
