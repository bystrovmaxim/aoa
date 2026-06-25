"""Tests for GetLeftMenuSidebarDataAction static string helpers."""

from __future__ import annotations

from aoa.maxitor.model.core.actions.left_sidebar_action import GetLeftMenuSidebarDataAction

_label = GetLeftMenuSidebarDataAction._diagram_view_label
_title = GetLeftMenuSidebarDataAction._lifecycle_state_machine_row_title


def test_diagram_view_label_idempotent() -> None:
    assert _label("Full graph") == "Full graph view"
    assert _label("Full graph view") == "Full graph view"


def test_lifecycle_state_machine_sidebar_title() -> None:
    assert _title("lifecycle") == "Lifecycle view"
    assert _title("counterparty_linkage_lifecycle") == "Counterparty linkage lifecycle view"
    assert _title("scheme_dispute_clock_lifecycle") == "Scheme dispute clock lifecycle view"
    assert _title("") == "Lifecycle view"
