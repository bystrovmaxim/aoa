# src/action_machine/legacy/described_fields/__init__.py
"""
Described-fields package exports marker and validators.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

This package exposes the described-fields intent marker and helper validators
used by graph inspectors to enforce declared schema metadata contracts.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    Action class
        |
        v
    DescribedFieldsIntent marker
        |
        +--> validate_described_schema(...)
        +--> validate_described_schemas_for_action(...)
        |
        v
    described_fields_intent_inspector (graph build / validation phase)

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    from action_machine.legacy.described_fields import (
        DescribedFieldsIntent,
        validate_described_schema,
    )

    validate_described_schema(MyAction)

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Public API surface for described-fields intent validation.
CONTRACT: Expose marker + validators consumed by graph inspectors.
INVARIANTS: No runtime mutation; validation-only helpers.
FLOW: action metadata -> validators -> inspector-driven graph checks.
FAILURES: Schema/contract violations produce validation exceptions.
EXTENSION POINTS: Add new validators in marker module and export via __all__.
AI-CORE-END
"""

from action_machine.legacy.described_fields.marker import (
    DescribedFieldsIntent,
    validate_described_schema,
    validate_described_schemas_for_action,
)

__all__ = [
    "DescribedFieldsIntent",
    "validate_described_schema",
    "validate_described_schemas_for_action",
]
