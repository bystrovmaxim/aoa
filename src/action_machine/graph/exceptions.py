# src/action_machine/graph/exceptions.py
"""
Exceptions for ActionMachine metadata and graph construction.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

All errors raised while ``GateCoordinator.build()`` walks inspectors or while
inspectors validate facet payloads.

Keeping them in a dedicated module allows:
1. Hosts and coordinator to import without circular imports.
2. Callers to catch specific exception types.
3. Tests to assert with ``pytest.raises`` on concrete classes.

═══════════════════════════════════════════════════════════════════════════════
ERROR-HANDLING PHILOSOPHY
═══════════════════════════════════════════════════════════════════════════════

ActionMachine does not swallow graph errors. They surface when the graph is
built (typically once at startup) and messages name the offending classes,
inspectors, and keys.

Every exception here signals a **developer** mistake, not bad end-user input.
Fix the code and rebuild.

═══════════════════════════════════════════════════════════════════════════════
EXCEPTIONS
═══════════════════════════════════════════════════════════════════════════════

DuplicateNodeError
    Two inspectors produced the same ``"node_type:node_name"`` key. Raised
    during phase 1 (collect). The message names both inspectors for quick
    diagnosis.

InvalidGraphError
    Structural graph integrity failed during phase 2:
    - an edge references a missing node, or
    - structural edges (depends / connection) contain a cycle.

PayloadValidationError
    A ``FacetPayload`` field failed validation during phase 2:
    - empty ``node_type`` / ``node_name``, or
    - ``node_class`` is not a ``type``.
"""

from __future__ import annotations


class DuplicateNodeError(ValueError):
    """
    Two inspectors claimed the same graph node key.

    Raised in phase 1 when duplicate ``"node_type:node_name"`` keys cannot be
    merged. The message contains the key and both inspector names.

    Subclasses ``ValueError`` because this is a configuration conflict: two
    inspectors fight over one node.

    Typical causes:
    - two inspectors reuse the same ``node_type`` for one class without merge
      support, or
    - a child node name collides with another inspector's node.

    Attributes:
        key : str
            Conflicting graph key.
        first_inspector : str
            Inspector that registered the node first.
        second_inspector : str
            Inspector that detected the conflict.
    """

    def __init__(
        self,
        key: str,
        first_inspector: str,
        second_inspector: str,
    ) -> None:
        """
        Args:
            key: Conflicting ``"node_type:node_name"`` key.
            first_inspector: Inspector that created the node first.
            second_inspector: Inspector that triggered the conflict.
        """
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
    The facet graph failed structural validation.

    Raised in phase 2 when:

    1. **Referential integrity** — an edge names a target missing from the
       collected payloads (the target class was never materialized).

       Example: ``@depends(PaymentService)`` but ``PaymentService`` does not
       appear as a graph node.

    2. **Acyclicity** — structural edges (``is_structural=True``) form a cycle,
       detected via ``rustworkx.is_directed_acyclic_graph()`` on a scratch graph.

       Example: A → B → C → A.

    Informational edges (``is_structural=False``) are **not** checked for
    cycles — cyclic business links (e.g. Order ↔ Customer) are expected.

    Subclasses ``Exception`` (not ``ValueError``/``TypeError``) because this
    is a graph-shape failure, not a simple type/value issue.
    """

    pass


class PayloadValidationError(TypeError):
    """
    A ``FacetPayload`` field is invalid.

    Raised in phase 2 while checking mandatory fields:

    - ``node_type`` — non-empty string.
    - ``node_name`` — non-empty string.
    - ``node_class`` — Python ``type``.

    Subclasses ``TypeError`` because violations are essentially type/shape
    mistakes (empty identifiers, non-type ``node_class``, …).

    Typical causes:
    - inspector omitted ``node_type`` in ``_build_payload()``,
    - ``_make_node_name()`` ran on a broken class reference,
    - ``node_class`` contains an instance instead of a class.

    Attributes:
        node_class : type | object
            Value carried in the offending payload's ``node_class``.
        field_name : str
            Field that failed (``"node_type"``, ``"node_name"``, ``"node_class"``).
        detail : str
            Human-readable explanation.
    """

    def __init__(
        self,
        node_class: object,
        field_name: str,
        detail: str,
    ) -> None:
        """
        Args:
            node_class: Payload ``node_class`` field (may be invalid).
            field_name: Which field failed validation.
            detail: Explanation string.
        """
        self.node_class: object = node_class
        self.field_name: str = field_name
        self.detail: str = detail

        class_name = (
            node_class.__qualname__
            if isinstance(node_class, type)
            else repr(node_class)
        )
        super().__init__(
            f"Invalid FacetPayload for {class_name}: "
            f"field '{field_name}' — {detail}"
        )
