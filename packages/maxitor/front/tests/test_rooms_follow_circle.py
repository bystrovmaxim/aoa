# packages/maxitor/front/tests/test_rooms_follow_circle.py
"""Tests for the follow-circle rule: following may never close a circle, directly or through others."""

from __future__ import annotations

from maxitor.front.model.rooms.follow_circle import chain_head, leads_to, would_close_circle


def test_nobody_follows_anyone() -> None:
    """With no links, any follow is fine."""
    assert would_close_circle({}, "boris", "anna") is False


def test_a_direct_circle_is_refused() -> None:
    """Anna follows Boris, so Boris cannot follow Anna."""
    assert would_close_circle({"anna": "boris"}, "boris", "anna") is True


def test_an_indirect_circle_is_refused_both_ways() -> None:
    """Anna follows Boris and Vera follows Anna: Boris may follow neither of them."""
    follows = {"anna": "boris", "vera": "anna"}
    assert would_close_circle(follows, "boris", "anna") is True
    assert would_close_circle(follows, "boris", "vera") is True


def test_following_oneself_is_a_circle() -> None:
    """Following yourself is the smallest circle."""
    assert would_close_circle({}, "anna", "anna") is True


def test_a_chain_without_the_follower_is_fine() -> None:
    """Vera follows Anna; Boris following Vera makes a chain, not a circle."""
    assert would_close_circle({"vera": "anna"}, "boris", "vera") is False


def test_an_existing_unrelated_circle_does_not_hang() -> None:
    """Even links that already loop (which the rule never lets in) end the walk."""
    assert would_close_circle({"x": "y", "y": "x"}, "boris", "x") is False


def test_the_view_comes_from_the_end_of_the_chain() -> None:
    """Vera follows Boris, who follows Anna: Vera takes the view from Anna; Boris's chain ends at Anna too (spec 038)."""
    follows = {"vera": "boris", "boris": "anna", "anna": None}
    assert chain_head(follows, "vera") == "anna"
    assert chain_head(follows, "boris") == "anna"
    assert chain_head(follows, "anna") == "anna"


def test_a_chain_leads_to_everyone_on_it_and_no_one_else() -> None:
    """Anna's focus goes to Boris and to Vera through him; never to Gleb, who follows nobody, nor back to Anna."""
    follows = {"vera": "boris", "boris": "anna", "anna": None, "gleb": None}
    assert leads_to(follows, "vera", "anna") and leads_to(follows, "boris", "anna") and leads_to(follows, "vera", "boris")
    assert not leads_to(follows, "gleb", "anna")
    assert not leads_to(follows, "anna", "vera")
