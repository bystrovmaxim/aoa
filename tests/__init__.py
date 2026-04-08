# tests/__init__.py
"""
ActionMachine Test Suite (v2).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Complete test suite for the ActionMachine framework, built on a unified
domain model and shared fixtures. All tests use TestBench as a single
entry point for testing.

═══════════════════════════════════════════════════════════════════════════════
PRINCIPLES
═══════════════════════════════════════════════════════════════════════════════

1. UNIFIED DOMAIN MODEL. All working Actions, services, domains — in the
   domain/ package. Test files import from there. Inside tests, Actions
   are NOT created, except for intentionally broken classes to verify
   errors (no @meta, no summary, etc.).

2. AAA FORMAT. Each test is structured as Arrange–Act–Assert.
   Comments explain the scenario's essence to newcomers, not re-narrate
   the code. Each AAA block describes WHAT we prepare, WHAT we do,
   and WHAT we check — at the business-logic level.

3. TESTBENCH. All integration tests use TestBench — a single
   immutable entry point that runs the action on async and sync
   machines and compares results.

4. TESTS IN SUBFOLDERS. Test files never lie in the tests/ root.
   Each group — in its own subfolder by topic: smoke/, core/, roles/, etc.

5. COMPACTNESS. Each file tests one aspect of the system
   and contains 100-250 lines.
"""
