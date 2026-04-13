# tests/smoke/__init__.py
"""
Smoke tests — basic ActionMachine infrastructure checks.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Minimal tests confirming key components work: the coordinator collects metadata,
the machine runs the pipeline, and TestBench runs actions on async and sync machines.

If smoke tests pass, the infrastructure is sound and the rest of the suite can run.
If any fail, there is a fundamental problem.

═══════════════════════════════════════════════════════════════════════════════
FILES
═══════════════════════════════════════════════════════════════════════════════

- test_ping.py        — PingAction (minimal action, summary only).
- test_simple.py      — SimpleAction (regular + summary with checker).
- test_full.py        — FullAction (depends + connection + "manager" role).
- test_coordinator.py — GateCoordinator collects metadata for all Actions.
"""
