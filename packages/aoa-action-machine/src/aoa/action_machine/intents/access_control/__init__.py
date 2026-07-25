# packages/aoa-action-machine/src/aoa/action_machine/intents/access_control/__init__.py
"""Access-control verdict returned by ``machine.check`` without executing the action."""

from __future__ import annotations

from aoa.action_machine.intents.access_control.access_verdict import (
    FORBIDDEN_OBJECT,
    AllowedVerdict,
    BaseVerdict,
    FailErrorVerdict,
    FailSecurityVerdict,
)

__all__ = ["FORBIDDEN_OBJECT", "AllowedVerdict", "BaseVerdict", "FailErrorVerdict", "FailSecurityVerdict"]
