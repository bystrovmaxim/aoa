# tests/system_core/test_dot_path_navigator.py
"""DotPathNavigator.navigate_with_source edge cases."""

from __future__ import annotations

from aoa.action_machine.system_core.dot_path_navigator import _SENTINEL, DotPathNavigator


def test_navigate_with_source_empty_dotpath_returns_root_tuple() -> None:
    root = {"a": 1}
    assert DotPathNavigator.navigate_with_source(root, "") == (root, None, None)


def test_navigate_with_source_returns_parent_and_last_segment() -> None:
    root = {"user": {"id": 7}}
    value, source, last = DotPathNavigator.navigate_with_source(root, "user.id")
    assert value == 7
    assert source == {"id": 7}
    assert last == "id"


def test_navigate_with_source_missing_segment_returns_sentinel() -> None:
    root: dict[str, object] = {}
    value, source, last = DotPathNavigator.navigate_with_source(root, "missing.x")
    assert value is _SENTINEL
    assert source == root
    assert last == "missing"
