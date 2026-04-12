# src/action_machine/aspects/aspect_intent.py
"""
Aspect intent marker and aspect structure validators.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

This module defines the ``AspectIntent`` marker and validation helpers used by
the inspector/coordinator build path. It guarantees that classes declaring
aspect decorators satisfy structural pipeline rules before runtime execution.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

Decorators attach method metadata. Inspector/builder collects ordered aspect
entries and passes them to this module validators. Validation enforces:
``AspectIntent`` inheritance, summary uniqueness, regular->summary completeness, and
summary-last ordering.

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- If aspects are declared, class must inherit ``AspectIntent``.
- At most one ``summary`` aspect may exist.
- If ``regular`` aspects exist, a ``summary`` aspect is required.
- ``summary`` aspect must be the last declared aspect method.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Happy path:

    class CreateOrderAction(BaseAction, AspectIntent):
        @regular_aspect("Validate")
        async def validate_aspect(self, params, state, box, connections):
            return {"ok": True}

        @summary_aspect("Build result")
        async def build_result_summary(self, params, state, box, connections):
            return OrderResult(...)

Edge case:

    class BrokenAction(BaseAction, AspectIntent):
        @regular_aspect("Only regular")
        async def only_regular_aspect(self, params, state, box, connections):
            return {"x": 1}

    # validate_aspects(BrokenAction, aspects) -> ValueError

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

The module only validates structural contracts. It does not execute aspects and
does not validate business-level semantics inside aspect methods.
Validators can raise:
- ``TypeError`` for missing ``AspectIntent`` marker when aspects are declared.
- ``ValueError`` for invalid aspect structure (summary count/order requirements).

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Aspect intent validation module.
CONTRACT: Enforce structural aspect pipeline contract at metadata-build time.
INVARIANTS: marker inheritance, one summary max, regular requires summary, summary last.
FLOW: decorator metadata -> inspector list -> validators -> coordinator-ready snapshot.
FAILURES: TypeError for undeclared aspect intent, ValueError for invalid aspect structure.
EXTENSION POINTS: New aspect types must preserve validator assumptions or extend checks.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from typing import Any


class AspectIntent:
    """
    Intent marker: the action class **declares an aspect pipeline** (regular → summary).

    Decorating methods with ``@regular_aspect`` / ``@summary_aspect`` is only valid
    when ``AspectIntent`` appears in MRO; validators enforce pipeline shape (one
    summary last, etc.). This is not “permission for one decorator” but commitment
    to the whole aspect grammar checked at ``GateCoordinator.build()``.

    ═══════════════════════════════════════════════════════════════════════════
    AI-CORE-BEGIN
    ═══════════════════════════════════════════════════════════════════════════
    ROLE: Public aspect intent marker.
    CONTRACT: Classes with aspect decorators must include this marker in MRO.
    INVARIANTS: Pure marker, no state and no side effects.
    FLOW: consumed by inspector/validator when building aspect snapshots.
    FAILURES: missing marker triggers TypeError in validator.
    EXTENSION POINTS: reusable marker contract for custom action base classes.
    AI-CORE-END
    ═══════════════════════════════════════════════════════════════════════════
    """

    pass


def require_aspect_intent_marker(cls: type, aspects: list[Any]) -> None:
    """
    Require ``AspectIntent`` marker when aspects are declared.

    ═══════════════════════════════════════════════════════════════════════════
    AI-CORE-BEGIN
    ═══════════════════════════════════════════════════════════════════════════
    PURPOSE: enforce aspect intent contract for decorated classes.
    INPUT/OUTPUT: class + collected aspects -> pass or TypeError.
    SIDE EFFECTS: none.
    FAILURES: TypeError with inheritance guidance.
    AI-CORE-END
    ═══════════════════════════════════════════════════════════════════════════
    """
    if aspects and not issubclass(cls, AspectIntent):
        aspect_names = ", ".join(a.method_name for a in aspects)
        raise TypeError(
            f"Class {cls.__name__} declares aspects ({aspect_names}) "
            f"but does not inherit AspectIntent. Decorators @regular_aspect "
            f"and @summary_aspect are allowed only on classes inheriting "
            f"AspectIntent. Use BaseAction or add AspectIntent to the "
            f"inheritance chain."
        )


def validate_aspects(cls: type, aspects: list[Any]) -> None:
    """
    Validate summary/regular structural pipeline invariants.

    ═══════════════════════════════════════════════════════════════════════════
    AI-CORE-BEGIN
    ═══════════════════════════════════════════════════════════════════════════
    PURPOSE: enforce executable aspect pipeline shape.
    INPUT/OUTPUT: class + ordered aspects -> pass or ValueError.
    SIDE EFFECTS: none.
    FAILURES: ValueError for summary multiplicity, absence, or wrong order.
    AI-CORE-END
    ═══════════════════════════════════════════════════════════════════════════
    """
    if not aspects:
        return

    summaries = [a for a in aspects if a.aspect_type == "summary"]
    regulars = [a for a in aspects if a.aspect_type == "regular"]

    if len(summaries) > 1:
        names = ", ".join(s.method_name for s in summaries)
        raise ValueError(
            f"Class {cls.__name__} declares {len(summaries)} summary aspects "
            f"({names}); only one summary aspect is allowed."
        )

    if regulars and not summaries:
        raise ValueError(
            f"Class {cls.__name__} declares {len(regulars)} regular aspects "
            f"but has no summary aspect. Action pipelines must end with a "
            f"summary aspect that returns Result."
        )

    if summaries and aspects[-1].aspect_type != "summary":
        raise ValueError(
            f"Class {cls.__name__}: summary aspect '{summaries[0].method_name}' "
            f"must be declared last among aspect methods. "
            f"Current last aspect is '{aspects[-1].method_name}' "
            f"(type: {aspects[-1].aspect_type})."
        )
