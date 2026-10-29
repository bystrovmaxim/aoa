# packages/maxitor/tools/repo_graph_port/tests/conftest.py
"""Shared fixtures: a public GitHub address that git reads from a local folder."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def github_in(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A folder standing in for ``https://github.com/``: git rewrites that address to it, for every git call of the test."""
    folder = tmp_path / "github"
    folder.mkdir()
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", f"url.{folder.as_uri()}/.insteadOf")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", "https://github.com/")
    return folder
