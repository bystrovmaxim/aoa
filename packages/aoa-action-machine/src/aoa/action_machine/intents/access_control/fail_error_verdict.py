# packages/aoa-action-machine/src/aoa/action_machine/intents/access_control/fail_error_verdict.py
"""Nobody could tell: the check itself broke."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from aoa.action_machine.intents.access_control.base_verdict import BaseVerdict


class FailErrorVerdict(BaseVerdict):
    """Nobody could tell. The check itself broke -- a crash, a timeout, an operation
    nobody recognises.

    This is not a refusal and must never be stored as one, or a single database hiccup
    would keep answering "no" long after it was over.

    The reason is a fixed code, never the text of whatever actually broke. That text
    differs from one failure to the next, and anyone who can see the difference can use
    it to map out what exists -- the same problem ``FORBIDDEN_OBJECT`` solves.

    This is only what somebody who *asked* is told. When the action really runs,
    anything that is not ``AllowedVerdict`` stops it.
    """

    kind: str = Field(default="FailErrorVerdict", min_length=1)
    reason: str = Field(min_length=1)

    def __init__(self, reason: str, **kwargs: Any) -> None:
        kwargs["reason"] = reason
        super().__init__(**kwargs)
