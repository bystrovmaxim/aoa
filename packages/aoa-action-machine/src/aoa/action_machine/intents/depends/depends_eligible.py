# packages/aoa-action-machine/src/aoa/action_machine/intents/depends/depends_eligible.py
"""
``DependsEligible`` — protocol for classes that may appear as ``@depends`` targets.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Nominal marker (empty :class:`typing.Protocol`) inherited by framework types that
are allowed as the first argument to ``@depends(...)`` when the host uses
``DependsIntent[DependsEligible]`` (for example :class:`~aoa.action_machine.model.base_action.BaseAction`).
Runtime checks use ``issubclass`` against this protocol; only subclasses count
(structural conformance without inheritance is not enough).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class DependsEligible(Protocol):
    """
    AI-CORE-BEGIN
    ROLE: Nominal marker for dependency declaration targets.
    CONTRACT: Subclasses may be listed in ``@depends`` when the host bound is ``DependsEligible``.
    INVARIANTS: Empty protocol; checked via ``issubclass`` at decorator time.
    AI-CORE-END
    """

    pass
