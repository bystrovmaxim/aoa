# packages/aoa-maxitor/tests/test_rooms_pages.py
"""The settings a room accepts per page: names and values the viewers send (spec 028, data-model "PageSettings")."""

from __future__ import annotations

import pytest

from aoa.maxitor.model.rooms.pages import page_key, setting_error


@pytest.mark.parametrize(
    ("page", "name", "value"),
    [
        (page_key("domain-erd"), "layout", "gv-neato"),
        (page_key("domain-erd"), "domains", ["players"]),
        (page_key("domain-erd", domain="players"), "disabled_entities", ["players.Player"]),
        (page_key("domain-erd"), "disabled_kinds", []),
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
