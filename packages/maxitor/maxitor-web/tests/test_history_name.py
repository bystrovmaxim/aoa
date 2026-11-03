# packages/maxitor/maxitor-web/tests/test_history_name.py
"""A history is named after its graph file's folder, and its full path tells it from another of the same name (spec 056)."""

from __future__ import annotations

import pytest
from maxitor.web.model.core.history_address import PrivateHistory, PublicHistory, parse_history


def _public(link: str) -> PublicHistory:
    """The public history a link opens."""
    history = parse_history(link)
    assert isinstance(history, PublicHistory)
    return history


@pytest.mark.parametrize(
    ("path", "title", "full_path"),
    [
        ("packages/aoa-demo/graph.json", "aoa-demo", "bystrovmaxim/aoa/packages/aoa-demo"),
        ("packages/maxitor/maxitor-web/graph.json", "maxitor-web", "bystrovmaxim/aoa/packages/maxitor/maxitor-web"),
        ("packages/maxitor/tools/repo-graph-port/graph.json", "repo-graph-port", "bystrovmaxim/aoa/packages/maxitor/tools/repo-graph-port"),
        ("graph.json", "aoa", "bystrovmaxim/aoa"),
    ],
)
def test_a_public_history_is_named_after_its_graph_files_folder(path: str, title: str, full_path: str) -> None:
    """FR-001, FR-002: the last folder names it, the repository at the root; the full path joins the repository and the folder."""
    history = _public(f"https://github.com/bystrovmaxim/aoa/blob/main/{path}")
    assert (history.title, history.full_path) == (title, full_path)


def test_a_version_file_does_not_change_the_name() -> None:
    """A version file joined to the link names nothing: the graph file's folder does."""
    history = _public("https://github.com/bystrovmaxim/aoa/blob/main/packages/aoa-demo/graph.json?version_link=https%3A%2F%2Fgithub.com%2Fbystrovmaxim%2Faoa%2Fblob%2Fmain%2Fpyproject.toml")
    assert (history.title, history.full_path) == ("aoa-demo", "bystrovmaxim/aoa/packages/aoa-demo")


def test_the_branch_does_not_change_the_name() -> None:
    """FR-004: a link to a tag names the history as a link to the branch does."""
    assert _public("https://github.com/bystrovmaxim/gameoffer/blob/v1.2.0/packages/forecast-game-back/graph.json").title == "forecast-game-back"


def test_a_private_history_keeps_its_id_and_its_address() -> None:
    """FR-005: a private history's name is its id; its full path is its address, never its key."""
    history = parse_history("https://repo-graph-port.aoa.run/api/v1/history/orders#key=secret")
    assert isinstance(history, PrivateHistory)
    assert (history.title, history.full_path) == ("orders", "https://repo-graph-port.aoa.run/api/v1/history/orders")
    assert "secret" not in history.full_path
