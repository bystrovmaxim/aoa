# packages/maxitor/app/tests/test_launch.py
"""``maxitor-api`` runs the viewer, or names the extra when the viewer's dependencies are missing."""

from __future__ import annotations

import importlib
from types import SimpleNamespace

import pytest
from maxitor.viewer import launch


def _missing(name: str):
    """An ``import_module`` stand-in that fails as if ``name`` were not installed."""

    def fail(_module: str) -> object:
        raise ModuleNotFoundError(f"No module named {name!r}", name=name)

    return fail


def test_a_missing_viewer_dependency_names_the_extra(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """A dependency the ``viewer`` extra brings is missing: one line on standard error, exit 2."""
    monkeypatch.setattr(importlib, "import_module", _missing("uvicorn"))
    with pytest.raises(SystemExit) as stopped:
        launch.viewer()
    assert stopped.value.code == 2
    assert capsys.readouterr().err == 'maxitor-api needs the viewer: pip install "maxitor[viewer]"\n'


def test_an_unrelated_missing_module_is_not_hidden(monkeypatch: pytest.MonkeyPatch) -> None:
    """A module the extra does not bring is a real error, not a missing extra."""
    monkeypatch.setattr(importlib, "import_module", _missing("not_a_viewer_dependency"))
    with pytest.raises(ModuleNotFoundError, match="not_a_viewer_dependency"):
        launch.viewer()


def test_the_viewer_runs_when_it_is_installed(monkeypatch: pytest.MonkeyPatch) -> None:
    """With the extra installed, the command runs the viewer's own ``run``."""
    ran: list[bool] = []
    monkeypatch.setattr(importlib, "import_module", lambda _module: SimpleNamespace(run=lambda: ran.append(True)))
    launch.viewer()
    assert ran == [True]
