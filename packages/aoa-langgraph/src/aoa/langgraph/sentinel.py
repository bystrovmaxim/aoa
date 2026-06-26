# packages/aoa-langgraph/src/aoa/langgraph/sentinel.py
"""
UNSET sentinel — marks a mid-field before any node has produced its value.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``UNSET`` is the initial value of every produced field (``.mid()``) in the
LangGraph agent state. It is distinct from ``None`` and signals "not yet
produced" rather than "explicitly absent".

LangGraph rebuilds the state between nodes via ``schema(**input)`` — it never
calls ``AgentState.__getitem__``, so ``UNSET`` travels safely across framework
hops without raising. The raising check lives only in
``AgentState.__getitem__`` (node-facing reads) and ``_extract_output``
(final state extraction).

Produced fields are typed ``T | UnsetType`` with ``default=UNSET`` so that
``schema(**input)`` accepts the sentinel as a valid value on every hop.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    build()               mid-field typed T | UnsetType, default=UNSET
        │
        ▼
    LangGraph hop         schema(**input) — constructs state, UNSET is valid
        │
        ├── node reads state["x"]  → AgentState.__getitem__ → FieldNotReadyError
        └── node writes dict       → UNSET values never written back explicitly

"""

from __future__ import annotations


class UnsetType:
    """
    AI-CORE-BEGIN
        ROLE: Singleton sentinel for "field not yet produced by any node".
        CONTRACT: Distinct from None; falsy; travels across LangGraph hops safely.
        INVARIANTS: Exactly one instance (singleton via __new__); immutable.
    AI-CORE-END
    """

    _instance: UnsetType | None = None

    def __new__(cls) -> UnsetType:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return "UNSET"

    def __bool__(self) -> bool:
        return False


UNSET: UnsetType = UnsetType()
