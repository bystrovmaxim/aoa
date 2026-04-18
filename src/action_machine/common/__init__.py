# src/action_machine/common/__init__.py
"""
action_machine.common — cross-layer helpers (names, small utilities).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Holds **dependency-light** helpers shared by domain, model, graph, and runtime
without pulling heavy subsystems. Prefer this package over duplicating string
conventions across modules.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    domain / graph / inspectors
              │
              v
    action_machine.common.*  (pure functions, no coordinator imports)

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Modules here avoid importing ``GraphCoordinator``, machines, or adapters.
- Public surface is re-exported via ``__all__``.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Happy path::

    from action_machine.common import qualified_dotted_name

    qualified_dotted_name(MyClass)

Edge case:

    Import only what you need to keep compile graphs minimal.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- Not a dumping ground for business logic; keep helpers tiny and stateless.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Shared lightweight utilities package.
CONTRACT: Re-export stable helpers; no heavy graph/runtime side effects on import.
INVARIANTS: Pure helpers; __all__ defines public names.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from action_machine.common.qualified_name import qualified_dotted_name

__all__ = [
    "qualified_dotted_name",
]
