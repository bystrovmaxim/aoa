# tests/scripts/test_package_boundaries.py
"""The boundary check inside ``maxitor``: ``graph-builder`` stands alone; an import belongs to its longest prefix."""

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
        "maxitor": {"current_roots": ["maxitor/front"], "import_prefixes": ["maxitor.front"], "may_import": ["action_machine", "graph_builder"]},
        "examples": {"current_roots": ["aoa/demo"], "import_prefixes": ["aoa.demo"], "may_import": ["action_machine"]},
    },
    "standalone": {"graph_builder": {"roots": ["maxitor/graph_builder"], "import_prefixes": ["maxitor.graph_builder"], "forbid": ["maxitor.front"]}},
}


def _violations(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, owner_folder: str, source: str) -> list[str]:
    """Check a tree whose one module, in ``owner_folder``, holds ``source``; every other root is empty."""
    for folder in ("aoa/action_machine", "maxitor/front", "aoa/demo", "maxitor/graph_builder"):
        (tmp_path / folder).mkdir(parents=True, exist_ok=True)
    (tmp_path / owner_folder / "module.py").write_text(source, encoding="utf-8")
    checker = _checker()
    monkeypatch.setattr(checker, "REPO_ROOT", tmp_path)
    return [v.format() for v in checker.check_production(CONFIG) + checker.check_standalone(CONFIG)]


def test_graph_builder_importing_the_front_is_named(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """``maxitor.graph_builder`` must not import the front: one violation, naming file, line, owner and module."""
    found = _violations(tmp_path, monkeypatch, "maxitor/graph_builder", "import json\nfrom maxitor.front.api import app\n")
    assert found == ["maxitor/graph_builder/module.py:2: context 'graph_builder' must not import package 'maxitor.front' via 'maxitor.front.api'"]


def test_graph_builder_importing_aoa_is_named(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """``maxitor.graph_builder`` must not import AOA."""
    found = _violations(tmp_path, monkeypatch, "maxitor/graph_builder", "import aoa.action_machine\n")
    assert found == ["maxitor/graph_builder/module.py:1: context 'graph_builder' must not import package 'aoa' via 'aoa.action_machine'"]


def test_the_front_may_use_graph_builder(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The front imports the command's schemas: allowed."""
    assert _violations(tmp_path, monkeypatch, "maxitor/front", "from maxitor.graph_builder.schemas import graph_schema\n") == []


def test_an_import_belongs_to_its_longest_prefix(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The demo importing ``maxitor.graph_builder`` is a violation against ``graph-builder``, not lost and not charged to ``maxitor``."""
    found = _violations(tmp_path, monkeypatch, "aoa/demo", "from maxitor.graph_builder.schemas import graph_schema\n")
    assert found == ["aoa/demo/module.py:1: context 'examples' must not import package 'graph_builder' via 'maxitor.graph_builder.schemas'"]
