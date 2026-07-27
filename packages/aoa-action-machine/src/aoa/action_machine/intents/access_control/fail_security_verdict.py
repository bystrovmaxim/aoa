# packages/aoa-action-machine/src/aoa/action_machine/intents/access_control/fail_security_verdict.py
"""No: somebody looked at who is asking and refused."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from aoa.action_machine.intents.access_control.base_verdict import BaseVerdict


class FailSecurityVerdict(BaseVerdict):
    """No. The check ran, looked at who is asking, and refused.

    Write the reason first: ``FailSecurityVerdict("FORBIDDEN_ROLE")``. It cannot be
    empty -- a refusal that says nothing leaves the caller with nowhere to go.
    """

    kind: str = Field(default="FailSecurityVerdict", min_length=1)
    reason: str = Field(min_length=1)

    def __init__(self, reason: str, **kwargs: Any) -> None:
        kwargs["reason"] = reason
        super().__init__(**kwargs)
