"""
ActionMachine root package.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provides the top-level Python package boundary for the ActionMachine framework.
This module is intentionally lightweight: it defines package identity and keeps
room for future stable root-level exports.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    External apps / tests
             |
             v
      import action_machine
             |
             v
    action_machine package root (__init__)
             |
     +-------+--------+-------------------+
     |       |        |                   |
  intents   model   runtime   resources/testing/...

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    import action_machine
    from action_machine.testing import TestBench

    bench = TestBench()

    # Edge case: root import itself does not initialize machines/resources.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Package boundary marker.
CONTRACT: Keep root import safe, side-effect free, and semantically stable.
INVARIANTS: No orchestration logic, no dynamic runtime initialization.
═══════════════════════════════════════════════════════════════════════════════
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""
