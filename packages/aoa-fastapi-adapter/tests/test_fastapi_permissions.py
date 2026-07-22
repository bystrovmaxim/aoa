# tests/test_fastapi_permissions.py
"""
Tests for ``aoa.fastapi.permissions`` — endpoint ``operation`` resolution (issue #130).

Validate ``build_route_index`` against real ``FastApiRouteRecord`` instances:
``operation`` is the endpoint identifier ``"{method} {path}"``, the index is a
projection of the adapter's routes (not the graph), and a duplicate (method, path)
is first-wins like the router — not an error.
"""

from aoa.fastapi.permissions import build_route_index, canonical_key
from aoa.fastapi.route_record import FastApiRouteRecord

from .support import CancelOrderAction, PingAction, SimpleAction


class TestBuildRouteIndex:
    """``build_route_index`` — ``{"{method} {path}": route record}`` from registered routes."""

    def test_empty_routes_yield_empty_index(self) -> None:
        assert build_route_index([]) == {}

    def test_indexes_by_operation(self) -> None:
        routes = [
            FastApiRouteRecord(action_class=CancelOrderAction, method="post", path="/actions/cancel-order"),
            FastApiRouteRecord(action_class=PingAction, method="get", path="/ping"),
        ]

        index = build_route_index(routes)

        assert set(index) == {"POST /actions/cancel-order", "GET /ping"}
        assert index["POST /actions/cancel-order"].action_class is CancelOrderAction
        assert index["GET /ping"].action_class is PingAction

    def test_same_action_on_two_operations_yields_two_entries(self) -> None:
        routes = [
            FastApiRouteRecord(action_class=SimpleAction, method="post", path="/a"),
            FastApiRouteRecord(action_class=SimpleAction, method="get", path="/a"),
        ]

        assert set(build_route_index(routes)) == {"POST /a", "GET /a"}

    def test_duplicate_operation_is_first_wins_not_an_error(self) -> None:
        # Same (method, path) registered twice — the second is unreachable in HTTP
        # routing anyway; the index keeps the first and raises nothing.
        routes = [
            FastApiRouteRecord(action_class=PingAction, method="post", path="/a"),
            FastApiRouteRecord(action_class=SimpleAction, method="post", path="/a"),
        ]

        index = build_route_index(routes)

        assert len(index) == 1
        assert index["POST /a"].action_class is PingAction


class TestCanonicalKey:
    """``canonical_key`` — the dedup-key half of ``(operation, canonical_key(params))``."""

    def test_same_fields_different_order_produce_the_same_key(self) -> None:
        assert canonical_key({"order_id": 7, "note": "urgent"}) == canonical_key({"note": "urgent", "order_id": 7})

    def test_different_values_produce_different_keys(self) -> None:
        assert canonical_key({"order_id": 7}) != canonical_key({"order_id": 8})

    def test_empty_params_is_a_stable_key(self) -> None:
        assert canonical_key({}) == canonical_key({})
