# tests/domain/test_relation_markers.py
"""
Tests for relation **markers**: `Inverse`, `NoInverse`, and `Rel`.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Markers annotate entity relation fields (`Annotated[..., Inverse(...)]`, etc.).
These tests assert constructor validation, repr, equality for the singleton
`NoInverse`, and **frozen** instances (no attribute assignment after creation).

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- **TypeError** — wrong types for `Inverse` / `Rel` arguments.
- **ValueError** — empty `Inverse.field_name`.
- **AttributeError** — mutation on frozen marker instances.

Does not cover ``NodeGraphCoordinator`` or entity graph assembly — only the marker
types themselves.
"""

import pytest

from aoa.action_machine.domain.relation_markers import Inverse, NoGraphEdge, NoInverse, Rel


class _Entity:
    pass


def test_inverse_ok() -> None:
    inv = Inverse(_Entity, "orders")
    assert inv.target_entity is _Entity
    assert inv.field_name == "orders"
    assert repr(inv) == "Inverse(_Entity, 'orders')"


def test_inverse_target_not_type() -> None:
    with pytest.raises(TypeError, match="Inverse: target_entity must be a type"):
        Inverse("not_a_type", "orders")  # type: ignore[arg-type]


def test_inverse_field_name_not_str() -> None:
    with pytest.raises(TypeError, match="Inverse: field_name must be str"):
        Inverse(_Entity, 123)  # type: ignore[arg-type]


def test_inverse_field_name_none_rejected() -> None:
    with pytest.raises(TypeError, match="Inverse: field_name must be str"):
        Inverse(_Entity, None)  # type: ignore[arg-type]


def test_inverse_field_name_empty() -> None:
    with pytest.raises(ValueError, match="Inverse: field_name cannot be empty"):
        Inverse(_Entity, "   ")


def test_inverse_frozen() -> None:
    inv = Inverse(_Entity, "x")
    with pytest.raises(AttributeError, match="Inverse is frozen"):
        inv.target_entity = int  # type: ignore[misc]


def test_no_inverse_singleton_repr() -> None:
    assert repr(NoInverse()) == "NoInverse()"
    assert NoInverse() == NoInverse()
    assert NoInverse() != object()
    assert hash(NoInverse()) == hash(NoInverse())


def test_no_inverse_frozen() -> None:
    n = NoInverse()
    with pytest.raises(AttributeError, match="NoInverse is frozen"):
        n.x = 1  # type: ignore[misc]
    with pytest.raises(AttributeError, match="NoInverse is frozen"):
        del n.x  # type: ignore[attr-defined]


def test_no_graph_edge_degenerate_semantics() -> None:
    marker = NoGraphEdge()
    assert repr(marker) == "NoGraphEdge()"
    assert marker == NoGraphEdge()
    assert marker != object()
    assert hash(marker) == hash(NoGraphEdge())


def test_no_graph_edge_frozen() -> None:
    marker = NoGraphEdge()
    with pytest.raises(AttributeError, match="NoGraphEdge is frozen"):
        marker.x = 1  # type: ignore[misc]
    with pytest.raises(AttributeError, match="NoGraphEdge is frozen"):
        del marker.x  # type: ignore[attr-defined]


def test_rel_ok() -> None:
    r = Rel(description="Customer orders")
    assert r.description == "Customer orders"


def test_rel_description_not_str() -> None:
    with pytest.raises(TypeError, match="Rel: description must be str"):
        Rel(description=99)  # type: ignore[arg-type]


def test_rel_description_empty() -> None:
    with pytest.raises(ValueError, match="Rel: description cannot be empty"):
        Rel(description="  \t")


def test_rel_frozen() -> None:
    r = Rel(description="x")
    with pytest.raises(AttributeError, match="Rel is frozen"):
        r.description = "y"  # type: ignore[misc]
