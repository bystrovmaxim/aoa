# packages/aoa-action-machine/src/aoa/action_machine/intents/access_control/access_verdict.py
"""AccessVerdict — result of an access check without executing the action."""

from __future__ import annotations

from typing import Any

from pydantic import ConfigDict

from aoa.action_machine.model.base_action import BaseAction
from aoa.action_machine.model.base_schema import BaseSchema


class AccessVerdict(BaseSchema):
    """
    AI-CORE-BEGIN
        ROLE: Answer "can this run?" without executing the action.
        CONTRACT: allowed=True implies level/reason are None; allowed=False sets
            level to the cascade level (1 role, 2 guard, 3 access_decide) that
            rejected the check.
        INVARIANTS: Frozen, forbid-extra fields.
    AI-CORE-END
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    allowed: bool
    action: type[BaseAction[Any, Any]]
    level: int | None = None
    reason: str | None = None
