# src/action_machine/intents/aspects/aspect_intent.py
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

    @regular_aspect / @summary_aspect
                 |
                 v
     AspectIntentInspector collects own-class aspects (``vars(cls)``)
                 |
                 v
    require_aspect_intent_marker(...)
                 |
                 v
          validate_aspects(...)
                 |
                 v
      coordinator-ready aspect snapshot

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- If aspects are declared, class must inherit ``AspectIntent``.
- Structural checks apply to the aspect tuple produced for **that** class from its
  own namespace (see ``AspectIntentInspector``): inherited base methods are not
  merged into the child’s facet list—subclasses re-declare aspects and use
  ``super()`` inside overrides when extending parent behavior.
- At most one ``summary`` aspect may exist.
- If ``regular`` aspects exist, a ``summary`` aspect is required.
- ``summary`` aspect must be the last declared aspect method **on that class
  body** (declaration order in ``vars``).

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
INVARIANTS: marker inheritance; own-class aspect list; one summary max; regular
  requires summary; summary last in declaring class order.
FLOW: decorator metadata -> inspector list (vars-only) -> validators -> snapshot.
FAILURES: TypeError for undeclared aspect intent, ValueError for invalid aspect structure.
EXTENSION POINTS: New aspect types must preserve validator assumptions or extend checks.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from typing import Any


class AspectIntent:
    """
    Marker mixin declaring that an action owns an aspect pipeline.

    AI-CORE-BEGIN
    ROLE: Public aspect intent marker.
    CONTRACT: Classes with aspect decorators must include this marker in MRO.
    INVARIANTS: Pure marker, no state and no side effects.
    AI-CORE-END
    """

    pass


def require_aspect_intent_marker(cls: type, aspects: list[Any]) -> None:
    """
    Require ``AspectIntent`` marker when aspects are declared.
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
    Validate regular/summary structural pipeline invariants.
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
