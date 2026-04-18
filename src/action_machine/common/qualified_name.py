# src/action_machine/common/qualified_name.py
"""
qualified_dotted_name — stable ``module.qualname`` string for Python types.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provide a single shared implementation for interchange IDs, facet ``node_name``
bodies, and other graph keys that must match the dotted import path of a class
(including nested classes via ``__qualname__``).

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    type object (class)
              │
              v
    qualified_dotted_name(cls)
              │
              v
    "<module>.<qualname>"  |  "<qualname>" only when module is empty / "__main__"

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Output matches :meth:`BaseIntentInspector._make_node_name` with no suffix (same
  string policy as graph coordinators).
- ``__main__`` and missing ``__module__`` yield ``cls.__qualname__`` only.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Happy path::

    # class defined in package module
    qualified_dotted_name(MyClass)  # -> "my_pkg.sub.MyClass"

Edge case::

    # class defined in interactive / __main__
    qualified_dotted_name(MainClass)  # -> "MainClass" (no module prefix)

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- Expects a ``type`` instance; passing non-classes is undefined (callers should
  validate).

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Shared dotted class-path helper for graph and metadata keys.
CONTRACT: module + qualname when module is a real package name; else qualname only.
INVARIANTS: Aligned with inspector node naming; no I/O.
FLOW: read __module__ / __qualname__ -> single formatted string.
FAILURES: Caller responsibility for non-type inputs.
EXTENSION POINTS: Other name policies stay in callers if semantics diverge.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations


def qualified_dotted_name(cls: type) -> str:
    """
    Full dotted path for a class: ``<module>.<qualname>``.

    The same string policy as :meth:`BaseIntentInspector._make_node_name`
    without a suffix. For ``__main__`` or a missing ``__module__``, only
    ``__qualname__`` is returned.

    Args:
        cls: A ``type`` object (usually a declared class).

    Returns:
        Stable dotted class path for graph tooling and interchange payloads.
    """
    module = getattr(cls, "__module__", None)
    if module and module != "__main__":
        return f"{module}.{cls.__qualname__}"
    return cls.__qualname__
