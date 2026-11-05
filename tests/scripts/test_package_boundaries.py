# tests/scripts/test_package_boundaries.py
"""The boundary check: the core never imports the demo, the demo may use the core, a standalone root imports no AOA, and an import belongs to its longest prefix."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _checker() -> ModuleType:
    """``scripts/check_package_boundaries.py``, loaded as a module."""
    spec = importlib.util.spec_from_file_location("check_package_boundaries", REPO_ROOT / "scripts" / "check_package_boundaries.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses look their module up while the class is built
    spec.loader.exec_module(module)
    return module


CONFIG = {
    "packages": {
        "action_machine": {"current_roots": ["aoa/action_machine"], "import_prefixes": ["aoa.action_machine"], "may_import": []},
        "examples": {"current_roots": ["aoa/demo"], "import_prefixes": ["examples", "aoa.demo"], "may_import": ["action_machine"]},
    },
    "standalone": {"tool": {"roots": ["tool"], "import_prefixes": ["aoa.action_machine.tool"], "forbid": ["aoa.demo"]}},
}


def _violations(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, owner_folder: str, source: str) -> list[str]:
    """Check a tree whose one module, in ``owner_folder``, holds ``source``; every other root is empty."""
    for folder in ("aoa/action_machine", "aoa/demo", "tool"):
        (tmp_path / folder).mkdir(parents=True, exist_ok=True)
    (tmp_path / owner_folder / "module.py").write_text(source, encoding="utf-8")
    checker = _checker()
    monkeypatch.setattr(checker, "REPO_ROOT", tmp_path)
    return [v.format() for v in checker.check_production(CONFIG) + checker.check_standalone(CONFIG)]


def test_the_core_importing_the_demo_is_named(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """``aoa.action_machine`` must not import the demo: one violation, naming file, line, owner and module."""
    found = _violations(tmp_path, monkeypatch, "aoa/action_machine", "import json\nfrom aoa.demo.model import shop\n")
    assert found == ["aoa/action_machine/module.py:2: context 'action_machine' must not import package 'examples' via 'aoa.demo.model'"]


def test_the_demo_may_use_the_core(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The demo is built on the core: allowed."""
    assert _violations(tmp_path, monkeypatch, "aoa/demo", "from aoa.action_machine.model import BaseAction\n") == []


def test_a_standalone_root_importing_aoa_is_named(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A standalone root must import nothing of ``aoa``."""
    found = _violations(tmp_path, monkeypatch, "tool", "import aoa.action_machine\n")
    assert found == ["tool/module.py:1: context 'tool' must not import package 'aoa' via 'aoa.action_machine'"]


def test_an_import_belongs_to_its_longest_prefix(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The demo importing the standalone tool is a violation against the tool, not lost and not charged to the core."""
    found = _violations(tmp_path, monkeypatch, "aoa/demo", "from aoa.action_machine.tool import run\n")
    assert found == ["aoa/demo/module.py:1: context 'examples' must not import package 'tool' via 'aoa.action_machine.tool'"]
