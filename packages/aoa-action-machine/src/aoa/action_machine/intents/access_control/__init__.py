# packages/aoa-action-machine/src/aoa/action_machine/intents/access_control/__init__.py
"""Access-control verdict returned by ``machine.check`` without executing the action."""

from __future__ import annotations

from aoa.action_machine.intents.access_control.allowed_verdict import AllowedVerdict
from aoa.action_machine.intents.access_control.base_verdict import BaseVerdict
from aoa.action_machine.intents.access_control.fail_error_verdict import FailErrorVerdict
from aoa.action_machine.intents.access_control.fail_security_verdict import (
    FORBIDDEN_OBJECT,
    FailSecurityVerdict,
)

__all__ = ["FORBIDDEN_OBJECT", "AllowedVerdict", "BaseVerdict", "FailErrorVerdict", "FailSecurityVerdict"]
