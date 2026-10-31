# packages/maxitor/front/tests/test_rooms_pages.py
"""The settings a room accepts per page: names and values the viewers send (spec 028, data-model "PageSettings")."""

from __future__ import annotations

import pytest
from maxitor.front.model.rooms.pages import page_key, setting_error


@pytest.mark.parametrize(
    ("page", "name", "value"),
    [
        (page_key("domain-erd"), "layout", "gv-neato"),
        (page_key("domain-erd"), "domains", ["players"]),
        (page_key("domain-erd", domain="players"), "disabled_entities", ["players.Player"]),
        (page_key("domain-erd"), "disabled_kinds", []),
        (page_key("domain-erd"), "disabled_changes", ["unchanged"]),
        (page_key("domain-erd"), "paint", "kinds"),
        (page_key("domain-erd"), "paint_diff", "changes"),
        (page_key("domain-erd"), "one_hop", False),
        (page_key("use-case", domain="players"), "layout", "dot_tb"),
        (page_key("use-case", domain="players"), "boundary", True),
        (page_key("lifecycle-fsm", node="n", host="h"), "rankdir", "TB"),
    ],
)
def test_every_setting_a_viewer_sends_is_accepted(page: str, name: str, value: object) -> None:
    """Each page setting the client sends passes the server's check."""
    assert setting_error(page, name, value) is None


@pytest.mark.parametrize(
    ("page", "name", "value"),
    [
        (page_key("domain-erd"), "entities", ["players.Player"]),
        (page_key("use-case", domain="players"), "rankdir", "TB"),
        (page_key("domain-erd"), "one_hop", "yes"),
        (page_key("full-graph"), "layout", "gv-neato"),
    ],
)
def test_names_and_values_the_viewers_do_not_send_are_refused(page: str, name: str, value: object) -> None:
    """Old names, wrong types and settings a page does not have are refused with a reason."""
    assert setting_error(page, name, value)


def test_a_room_shares_the_map_s_filters_and_paint() -> None:
    page = page_key("full-graph")
    assert setting_error(page, "disabled_node_types", ["Entity"]) is None
    assert setting_error(page, "disabled_domains", ["a.Orders"]) is None
    assert setting_error(page, "disabled_changes", ["unchanged"]) is None
    assert setting_error(page, "paint", "kinds") is None
    assert setting_error(page, "paint_diff", "changes") is None
    assert setting_error(page, "paint", "changes") is not None
    assert setting_error(page, "disabled_node_types", "Entity") is not None
