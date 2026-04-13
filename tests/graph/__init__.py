# tests/graph/__init__.py
"""
Tests for ``action_machine.graph``: ``GateCoordinator``, intent inspectors, and facet snapshots.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

These tests exercise how declaration-time attributes on classes (written by
decorators) are read by **intent inspectors** during ``GateCoordinator.build()``,
how the graph and **facet snapshots** are produced, and how public coordinator APIs
behave. They do not reintroduce removed class-level introspection helpers on
``BaseAction`` — the production machine reads pipeline metadata from coordinator
snapshots only.

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Tests use the same coordinator registration and ``build()`` flow as production
  unless a case explicitly constructs a partial coordinator.
- Facet keys and payload shapes must match the corresponding inspector modules.

═══════════════════════════════════════════════════════════════════════════════
DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    Action / entity classes (tests fixtures, scenarios.domain_model)
              │
              ▼
    GateCoordinator.register(...).build()
              │
              ├────► test_*_intent_inspector.py   (per-facet collection)
              ├────► test_coordinator_*.py         (graph, snapshots, strict rules)
              └────► test_domain.py                (BaseDomain naming rules)

═══════════════════════════════════════════════════════════════════════════════
LAYOUT
═══════════════════════════════════════════════════════════════════════════════

    tests/graph/
    ├── __init__.py                     — this file
    ├── test_new_gate_coordinator_*.py  — graph build and facet accessors
    ├── test_*_intent_inspector.py   — individual facet inspectors
    ├── test_coordinator_graph.py       — graph API, nodes, edges, cycles
    ├── test_graph_skeleton_and_hydrate.py — skeleton/hydrate; stubs; action keys
    ├── test_coordinator_strict.py      — domain invariant and graph consistency
    └── test_domain.py                  — BaseDomain: name validation, inheritance

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Happy path: build a coordinator with default inspectors, assert ``is_built`` and
that ``get_snapshot(SomeAction, "aspect")`` returns expected rows.

Edge case: missing required decorator or structural cycle → build fails with the
documented exception type.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

Tests focus on graph build and facet snapshots, not full HTTP or DB adapters. Heavy integration
smoke lives under ``tests/smoke/``.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Test package init for graph / coordinator coverage.
CONTRACT: Describes scope; no runtime exports.
INVARIANTS: Coordinator snapshot model; no BaseAction scratch_* API.
FLOW: fixtures → coordinator build → assertions on graph and snapshots.
FAILURES: test failures map to coordinator or inspector regressions.
EXTENSION POINTS: add inspector tests alongside new facets.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""
