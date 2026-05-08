# tests/conftest.py
"""
Workspace-wide pytest configuration.

Keep this module free of imports from ``aoa.*`` or ``tests.action_machine`` so
``pytest tests/graph`` and other narrow zones do not pull ActionMachine fixtures.
Action-scenario fixtures live in ``tests/action_machine/conftest.py``.
"""
