# src/graph/exceptions.py
"""
Exceptions for ActionMachine metadata and graph construction.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

All errors raised during metadata graph assembly (interchange snapshots, validation,
projection) or while inspectors validate payloads.

Keeping them in a dedicated module allows:
1. Hosts and coordinator to import without circular imports.
2. Callers to catch specific exception types.
3. Tests to assert with ``pytest.raises`` on concrete classes.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    inspectors collect payloads
            │
            ├─ duplicate key conflict ---------> DuplicateNodeError
            │
            └─ phase-2 validation
                 ├─ invalid payload shape -----> PayloadValidationError
                 └─ broken graph integrity ----> InvalidGraphError

═══════════════════════════════════════════════════════════════════════════════
ERROR-HANDLING PHILOSOPHY
═══════════════════════════════════════════════════════════════════════════════

ActionMachine does not swallow graph errors. They surface when the graph is
built (typically once at startup) and messages name the offending classes,
inspectors, and keys.

Every exception here signals a **developer** mistake, not bad end-user input.
Fix the code and rebuild.
"""

from __future__ import annotations


class DuplicateNodeError(ValueError):
    """
    AI-CORE-BEGIN
    ROLE: Phase-1 ``collect`` failure: two inspectors emit the same ``node_type:node_name`` key and merge cannot reconcile them.
    CONTRACT: ``ValueError`` subclass; ``key``, ``first_inspector``, ``second_inspector`` on the instance; ``str()`` message repeats all three for pytest and logs.
    INVARIANTS: Configuration / inspector conflict only (not end-user input).
    FAILURES: Duplicate ``node_type`` without merge support, or colliding child node names between inspectors.
    AI-CORE-END
    """

    def __init__(
        self,
        key: str,
        first_inspector: str,
        second_inspector: str,
    ) -> None:
        """Set conflicting key and the two inspectors involved in the collision."""
        self.key: str = key
        self.first_inspector: str = first_inspector
        self.second_inspector: str = second_inspector
        super().__init__(
            f"Node key conflict '{key}':\n"
            f"  created by:    {first_inspector}\n"
            f"  conflict with: {second_inspector}"
        )


class InvalidGraphError(Exception):
    """
    AI-CORE-BEGIN
    ROLE: Phase-2 graph integrity: referential break (edge target never materialized) or structural-edge cycle.
    CONTRACT: Plain ``Exception``; message is coordinator/graph-builder diagnostic (targets, cycle path context as available).
    INVARIANTS: Only structural edges participate in acyclicity checks; ``is_structural=False`` edges may cycle by design.
    FAILURES: Missing payload for ``target_node_type:target_name``, or ``rustworkx`` DAG check fails on structural slice.
    AI-CORE-END
    """

    pass


class PayloadValidationError(TypeError):
    """
    AI-CORE-BEGIN
    ROLE: Phase-2 inspector graph-node payload shape check: ``node_type``, ``node_name``, ``node_class`` must be valid non-empty / ``type`` as applicable.
    CONTRACT: ``TypeError`` subclass; ``node_class``, ``field_name``, ``detail`` on the instance; ``str()`` includes class repr and field.
    INVARIANTS: Developer/inspector bug class (empty ids, wrong ``node_class`` kind), not runtime user validation.
    FAILURES: Omitted fields in ``_build_payload``, bad class ref in name helpers, non-type where a class is required.
    AI-CORE-END
    """

    def __init__(
        self,
        node_class: object,
        field_name: str,
        detail: str,
    ) -> None:
        """Record invalid ``node_class``, failing ``field_name``, and explanation."""
        self.node_class: object = node_class
        self.field_name: str = field_name
        self.detail: str = detail

        class_name = (
            node_class.__qualname__
            if isinstance(node_class, type)
            else repr(node_class)
        )
        super().__init__(
            f"Invalid inspector graph node payload for {class_name}: "
            f"field '{field_name}' — {detail}"
        )
