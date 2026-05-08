# packages/aoa-action-machine/src/aoa/action_machine/__init__.py
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

"""
