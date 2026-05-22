# packages/aoa-examples/aoa_examples_tests/conftest.py
"""Fixtures and import bootstrap for example package tests."""

from __future__ import annotations

# Breaks ActionMachine import cycles when this test tree is collected in isolation.
from aoa.action_machine.testing import TestBench  # noqa: F401  # pylint: disable=unused-import
