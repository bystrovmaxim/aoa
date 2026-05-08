# packages/aoa-action-machine/src/aoa/action_machine/intents/aspects/aspect_intent.py
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
     Interchange aspect nodes (graph model collectors) derive from own-class declarations
                 |
                 v
    require_aspect_intent_marker(...)
                 |
                 v
          validate_aspects(...)
                 |
                 v
      coordinator-ready aspect snapshot

"""

from __future__ import annotations

from typing import Any


class AspectIntent:
    """
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
