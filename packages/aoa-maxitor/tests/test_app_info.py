# packages/aoa-maxitor/tests/test_app_info.py
"""
App info — which Maxitor is running: the package version and the client build it serves.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``GET /api/meta/app-info`` answers through ``AppInfoAction``; the build comes from the
``build.json`` the client build writes next to the bundle, read by
``StaticBundleResource``. A missing or unreadable file means "no built client" and
reads as an empty build, never as an error.
"""

from __future__ import annotations

from importlib.metadata import version
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from aoa.maxitor.api.app import create_app
from aoa.maxitor.model.core.resources.static_bundle_resource import StaticBundleResource


def test_app_info_names_the_version_and_the_build(monkeypatch: pytest.MonkeyPatch) -> None:
    """The route answers the installed version and the bundle's build."""
    monkeypatch.setattr(StaticBundleResource, "build", lambda self: "abc123def456")
    with TestClient(create_app()) as client:
        response = client.get("/api/meta/app-info")
    assert response.status_code == 200
    assert response.json() == {"version": version("aoa-maxitor"), "build": "abc123def456"}


def test_the_bundle_reads_its_build(tmp_path: Path) -> None:
    """A build.json written by the client build gives its id."""
    (tmp_path / "build.json").write_text('{"build": "abc123def456"}', encoding="utf-8")
    assert StaticBundleResource(tmp_path).build() == "abc123def456"


@pytest.mark.parametrize("content", [None, "not json", '["abc"]', '{"build": 7}'])
def test_a_missing_or_broken_build_file_reads_as_no_build(tmp_path: Path, content: str | None) -> None:
    """No file, broken JSON, or a wrong shape all read as an empty build."""
    if content is not None:
        (tmp_path / "build.json").write_text(content, encoding="utf-8")
    assert StaticBundleResource(tmp_path).build() == ""
