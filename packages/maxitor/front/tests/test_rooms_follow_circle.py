# packages/maxitor/front/tests/test_rooms_follow_circle.py
"""Tests for the follow-circle rule: following may never close a circle, directly or through others."""

from __future__ import annotations

from maxitor.front.model.rooms.follow_circle import would_close_circle


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
