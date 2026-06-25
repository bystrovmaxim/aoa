# tests/bench/__init__.py
"""
Tests for ``TestBench`` — single entry point for comparing action runs across machines.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``TestBench`` is an immutable fluent helper that holds async and sync machines,
runs the same action through each, and compares results. Any divergence raises
``ResultMismatchError``. This package groups tests by concern (creation,
immutability, full run, single aspect, summary, mocks, comparison, stubs).

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Bench instances are not mutated by ``with_*`` methods; they return new benches.
- Shared actions live under ``tests/scenarios/domain_model/`` (see layout below).

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    TestBench.with_machines(async_m, sync_m)
              │
              ▼
         .run(context, action, params)
              │
              ├── async machine  ──► BaseResult
              └── sync machine   ──► BaseResult
              │
              ▼
         compare → ResultMismatchError on mismatch

═══════════════════════════════════════════════════════════════════════════════
LAYOUT
═══════════════════════════════════════════════════════════════════════════════

- ``test_bench_creation.py`` — construction and parameter storage.
- ``test_bench_immutability.py`` — fluent methods return new benches.
- ``test_bench_run.py`` — full ``run()``.
- ``test_bench_run_aspect.py`` / ``test_bench_run_summary.py`` — scoped runs.
- ``test_mock_action.py`` — ``MockAction`` fixed vs computed results.
- ``test_comparison.py`` — cross-machine result comparison.
- ``test_state_validator.py`` — state validation before aspects.
- ``test_stubs.py`` — context stubs (e.g. ``UserInfoStub``).
- ``test_bench_edges.py`` — edge cases for bench helpers.

**Domain actions** (``tests/scenarios/domain_model/``): ``PingAction``, ``SimpleAction``,
``FullAction``, ``ChildAction``, ``AdminAction``. Shared fixtures
(``bench``, ``clean_bench``, ``manager_bench``, mocks) live in ``tests/conftest.py``.

"""
