# packages/aoa-action-machine/src/aoa/action_machine/intents/access_control/fail_error_verdict.py
"""Nobody could tell: the check itself broke."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from aoa.action_machine.intents.access_control.base_verdict import BaseVerdict


class FailErrorVerdict(BaseVerdict):
    """
    AI-CORE-BEGIN
        ROLE: The "nobody could tell" of the three access-check answers — the check
              itself broke: a crash, a timeout, an operation nobody recognises.
        CONTRACT: Takes the reason first (``FailErrorVerdict("UNKNOWN_ENDPOINT")``);
                  kind is "FailErrorVerdict". The reason is a fixed code chosen by the
                  framework, never text taken from the failure.
        INVARIANTS: reason is present and never empty. Never treated or stored as a
                    refusal.
    AI-CORE-END

    This is the absence of a decision, not a decision to say no, and storing it as one
    would let a single database hiccup keep answering "no" long after it was over.

    The reason is a fixed code, never the text of whatever actually broke. That text
    differs from one failure to the next, and anyone who can see the difference can use
    it to map out what exists -- the same problem ``FORBIDDEN_OBJECT`` solves.

    This is only what somebody who *asked* is told. When the action really runs,
    anything that is not ``AllowedVerdict`` stops it.
    """

    reason: str = Field(min_length=1)

    def __init__(self, reason: str, kind: str = "FailErrorVerdict", **kwargs: Any) -> None:
        super().__init__(kind=kind, reason=reason, **kwargs)
