# packages/aoa-action-machine/src/aoa/action_machine/intents/access_control/fail_security_verdict.py
"""No: somebody looked at who is asking and refused."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from aoa.action_machine.intents.access_control.base_verdict import BaseVerdict


class FailSecurityVerdict(BaseVerdict):
    """
    AI-CORE-BEGIN
        ROLE: The "no" of the three access-check answers — the check ran, looked at who
              is asking, and refused. A real decision, safe to remember and reuse.
        CONTRACT: Takes the reason first (``FailSecurityVerdict("FORBIDDEN_ROLE")``);
                  kind is "FailSecurityVerdict". A subclass may add fields of its own
                  and still get the positional reason.
        INVARIANTS: reason is present and never empty.
    AI-CORE-END

    A refusal that says nothing leaves the caller with nowhere to go, which is why the
    reason is required. What it may say is a separate question: see FORBIDDEN_OBJECT for
    the case where a precise reason would tell an outsider something they should not
    learn.
    """

    reason: str = Field(min_length=1)

    def __init__(self, reason: str, kind: str = "FailSecurityVerdict", **kwargs: Any) -> None:
        super().__init__(kind=kind, reason=reason, **kwargs)
