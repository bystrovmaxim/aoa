# tests/runtime/test_runtime_package_lazy_import.py
"""Lazy ``CoreActionMachine`` export on ``action_machine.runtime``."""

from __future__ import annotations

import importlib

import pytest


def test_runtime_package_exposes_core_action_machine() -> None:
    rt = importlib.import_module("action_machine.runtime")
    from action_machine.runtime.machines.core_action_machine import CoreActionMachine

    assert rt.CoreActionMachine is CoreActionMachine


def test_runtime_getattr_unknown_name_raises() -> None:
    rt = importlib.import_module("action_machine.runtime")
    unknown = "NotARealRuntimeExport"
    with pytest.raises(AttributeError, match="has no attribute"):
        _ = getattr(rt, unknown)
