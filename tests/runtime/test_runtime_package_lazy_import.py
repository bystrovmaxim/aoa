# tests/runtime/test_runtime_package_lazy_import.py
"""Smoke tests for ``action_machine.runtime`` package surface."""

from __future__ import annotations

import importlib

import pytest


def test_runtime_package_core_removed() -> None:
    rt = importlib.import_module("action_machine.runtime")
    with pytest.raises(AttributeError, match="has no attribute"):
        _ = rt.Core


def test_runtime_getattr_unknown_name_raises() -> None:
    rt = importlib.import_module("action_machine.runtime")
    unknown = "NotARealRuntimeExport"
    with pytest.raises(AttributeError, match="has no attribute"):
        _ = getattr(rt, unknown)
