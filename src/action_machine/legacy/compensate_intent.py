# src/action_machine/legacy/compensate_intent.py
"""
Compensate intent marker mixin.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Define ``CompensateIntent`` marker mixin for classes that declare ``@compensate``
methods. Build-time binding checks (marker presence, aspect targets, uniqueness)
run in the graph builder / coordinator layer.
"""


class CompensateIntent:
    """
    Marker mixin declaring eligibility for ``@compensate`` methods.

    AI-CORE-BEGIN
    ROLE: Compensator grammar marker for action classes.
    CONTRACT: Classes with compensators must include this mixin in MRO.
    INVARIANTS: Pure marker; no behavior or state.
    AI-CORE-END
    """

    pass
