# tests/scripts/test_package_boundaries.py
"""The boundary check inside ``maxitor``: ``gnomon`` stands alone; an import belongs to its longest prefix."""

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
        "maxitor": {"current_roots": ["maxitor/viewer"], "import_prefixes": ["maxitor.viewer"], "may_import": ["action_machine", "gnomon"]},
        "examples": {"current_roots": ["aoa/demo"], "import_prefixes": ["aoa.demo"], "may_import": ["action_machine"]},
    },
    "standalone": {"gnomon": {"roots": ["maxitor/gnomon"], "import_prefixes": ["maxitor.gnomon"], "forbid": ["maxitor.viewer"]}},
}


def _violations(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, owner_folder: str, source: str) -> list[str]:
    """Check a tree whose one module, in ``owner_folder``, holds ``source``; every other root is empty."""
    for folder in ("aoa/action_machine", "maxitor/viewer", "aoa/demo", "maxitor/gnomon"):
        (tmp_path / folder).mkdir(parents=True, exist_ok=True)
    (tmp_path / owner_folder / "module.py").write_text(source, encoding="utf-8")
    checker = _checker()
    monkeypatch.setattr(checker, "REPO_ROOT", tmp_path)
    return [v.format() for v in checker.check_production(CONFIG) + checker.check_standalone(CONFIG)]


def test_gnomon_importing_the_viewer_is_named(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """``maxitor.gnomon`` must not import the viewer: one violation, naming file, line, owner and module."""
    found = _violations(tmp_path, monkeypatch, "maxitor/gnomon", "import json\nfrom maxitor.viewer.api import app\n")
    assert found == ["maxitor/gnomon/module.py:2: context 'gnomon' must not import package 'maxitor.viewer' via 'maxitor.viewer.api'"]


def test_gnomon_importing_aoa_is_named(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """``maxitor.gnomon`` must not import AOA."""
    found = _violations(tmp_path, monkeypatch, "maxitor/gnomon", "import aoa.action_machine\n")
    assert found == ["maxitor/gnomon/module.py:1: context 'gnomon' must not import package 'aoa' via 'aoa.action_machine'"]


def test_the_viewer_may_use_gnomon(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The viewer imports the command's schemas: allowed."""
    assert _violations(tmp_path, monkeypatch, "maxitor/viewer", "from maxitor.gnomon.schemas import graph_schema\n") == []


def test_an_import_belongs_to_its_longest_prefix(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The demo importing ``maxitor.gnomon`` is a violation against ``gnomon``, not lost and not charged to ``maxitor``."""
    found = _violations(tmp_path, monkeypatch, "aoa/demo", "from maxitor.gnomon.schemas import graph_schema\n")
    assert found == ["aoa/demo/module.py:1: context 'examples' must not import package 'gnomon' via 'maxitor.gnomon.schemas'"]
