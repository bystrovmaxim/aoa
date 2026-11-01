"""The rules of ``scripts/check_no_secrets.py``: which files are forbidden, which are read, what is new."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "check_no_secrets.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_no_secrets", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_no_secrets"] = module
    spec.loader.exec_module(module)
    return module


check = _load()


def test_secret_files_are_found_by_name_anywhere() -> None:
    paths = [".env", "deploy/stand/.env", ".env.production", "certs/server.pem", "certs/read.key"]
    assert check.secret_files(paths) == paths


def test_an_example_and_ordinary_names_are_not_secret_files() -> None:
    paths = [".env.example", "deploy/stand/.env.example", "docs/env.md", "src/key.py", "a.env.py"]
    assert check.secret_files(paths) == []


def test_generated_and_sample_paths_are_not_scanned() -> None:
    paths = ["specs/025/data/baseline.json", "examples/step/01.ipynb", "packages/aoa-demo/graph.json", "tests/a.py"]
    assert check.scanned_files(paths) == []


def test_a_tracked_source_file_is_scanned() -> None:
    assert check.scanned_files(["scripts/check_no_secrets.py"]) == ["scripts/check_no_secrets.py"]


def test_only_an_unreviewed_finding_is_new() -> None:
    reviewed = ("README.md", "Secret Keyword", "aaa")
    unreviewed = ("README.md", "Secret Keyword", "bbb")
    assert check.new_findings({reviewed, unreviewed}, {reviewed}) == [unreviewed]
