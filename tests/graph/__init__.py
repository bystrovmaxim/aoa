# tests/graph/__init__.py
"""
Tests for ``graph``: ``GraphCoordinator``, intent inspectors, and facet snapshots.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

These tests exercise how declaration-time attributes on classes (written by
decorators) are read by **intent inspectors** during ``GraphCoordinator.build()``,
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
    GraphCoordinator.register(...).build()
              │
              ├────► test_*_intent_inspector.py   (per-facet collection)
              ├────► tests/scenarios/graph_with_runtime/test_coordinator_*.py
              │      (graph + runtime / integrations — cross-layer)
              └────► test_domain.py                (BaseDomain naming rules)

═══════════════════════════════════════════════════════════════════════════════
LAYOUT
═══════════════════════════════════════════════════════════════════════════════

    tests/graph/
    ├── __init__.py                     — this file
    ├── test_*_intent_inspector.py      — individual facet inspectors
    └── test_domain.py                  — BaseDomain: name validation, inheritance

    tests/scenarios/graph_with_runtime/
    ├── test_new_gate_coordinator_*.py  — graph build with runtime machine
    ├── test_coordinator_graph.py       — graph API, nodes, edges, cycles
    ├── test_graph_skeleton_and_hydrate.py
    ├── test_coordinator_strict.py
    └── …                               — other coordinator + runtime cases

"""
