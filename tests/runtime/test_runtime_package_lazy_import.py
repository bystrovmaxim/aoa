# tests/runtime/test_runtime_package_lazy_import.py
"""Lazy ``Core`` export on ``action_machine.runtime``."""

from __future__ import annotations

import importlib

import pytest


def test_runtime_package_exposes_core() -> None:
    rt = importlib.import_module("action_machine.runtime")
    from action_machine.runtime.machines.core import Core

    assert rt.Core is Core


def test_runtime_getattr_unknown_name_raises() -> None:
    rt = importlib.import_module("action_machine.runtime")
    unknown = "NotARealRuntimeExport"
    with pytest.raises(AttributeError, match="has no attribute"):
        _ = getattr(rt, unknown)
