# src/action_machine/intents/compensate/compensate_intent.py
"""
Compensate intent marker and compensator binding validators.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Define ``CompensateIntent`` marker mixin and graph-time validators for
compensator declarations. This module enforces that:
- classes declaring compensators carry the marker, and
- compensators target existing regular aspects with unique bindings.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    @compensate(...) declarations
              |
              v
    inspector collects compensator entries
              |
              v
    require_compensate_intent_marker(...)
    validate_compensators(...)
              |
              v
    build-time compensator facet snapshot
              |
              v
    runtime rollback uses validated metadata

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- If compensators are declared, class must inherit ``CompensateIntent``.
- Target aspect must exist and must be ``regular`` (not ``summary``).
- One aspect may have at most one compensator.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- Raises ``TypeError`` for missing ``CompensateIntent`` marker.
- Raises ``ValueError`` for invalid target aspect or duplicate bindings.
- This module validates declaration topology only; runtime rollback execution
  happens in machine layer.


AI-CORE-BEGIN
ROLE: Compensator declaration marker + topology validator module.
CONTRACT: Ensure marker presence and regular-aspect binding integrity.
INVARIANTS: Deterministic, unique, and valid compensator target mapping.
FLOW: declaration metadata -> validators -> facet snapshot -> runtime rollback.
AI-CORE-END
"""

from __future__ import annotations

from typing import Any


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


def require_compensate_intent_marker(
    cls: type,
    compensators: list[Any],
) -> None:
    """Require ``CompensateIntent`` marker when compensators are declared."""
    if compensators and not issubclass(cls, CompensateIntent):
        names = ", ".join(c.method_name for c in compensators)
        raise TypeError(
            f"Class {cls.__name__} declares compensators ({names}) "
            f"but does not inherit CompensateIntent. The @compensate decorator "
            f"is valid only when CompensateIntent is present in MRO. "
            f"Use BaseAction or add CompensateIntent to the inheritance chain."
        )


def validate_compensators(
    cls: type,
    compensators: list[Any],
    aspects: list[Any],
) -> None:
    """Validate compensator bindings to existing regular aspects and uniqueness."""
    if not compensators:
        return

    aspect_map: dict[str, Any] = {a.method_name: a for a in aspects}
    seen_targets: dict[str, str] = {}

    for comp in compensators:
        target = comp.target_aspect_name

        if target not in aspect_map:
            available = ", ".join(sorted(aspect_map.keys())) if aspect_map else "(no aspects)"
            raise ValueError(
                f"Class {cls.__name__}: compensator '{comp.method_name}' "
                f"is bound to aspect '{target}', which does not exist. "
                f"Available aspects: {available}. "
                f"Check target_aspect_name in @compensate."
            )

        target_aspect = aspect_map[target]
        if target_aspect.aspect_type != "regular":
            raise ValueError(
                f"Class {cls.__name__}: compensator '{comp.method_name}' "
                f"is bound to aspect '{target}' with type "
                f"'{target_aspect.aspect_type}'. Compensators may target only "
                f"regular aspects. Summary aspects produce final Result and do "
                f"not perform side effects requiring rollback."
            )

        if target in seen_targets:
            existing_comp = seen_targets[target]
            raise ValueError(
                f"Class {cls.__name__}: aspect '{target}' has two "
                f"compensators: '{existing_comp}' and '{comp.method_name}'. "
                f"At most one compensator is allowed per aspect."
            )

        seen_targets[target] = comp.method_name
