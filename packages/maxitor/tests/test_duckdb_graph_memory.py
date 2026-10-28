# packages/maxitor/tests/test_duckdb_graph_memory.py
"""A built graph keeps no index and no primary key, and stays under a memory ceiling."""

from __future__ import annotations

from typing import Any

from maxitor.viewer.model.diagrams.resources.duckdb_graph_resource import DuckDBGraphResource

_MIB = 1024 * 1024
_CEILING_MIB = 1.75
_DOMAIN_ID = "d.default.Dom"
_LIFECYCLE_ID = "e.x.Entity:lifecycle:status"


def _payload() -> dict[str, Any]:
    """Return the tiny four-node coordinator payload used by the diagram route tests."""
    return {
        "schema_version": "1.0",
        "nodes": [
            {
                "id": _DOMAIN_ID,
                "label": _DOMAIN_ID,
                "type": "Domain",
                "properties": {"name": _DOMAIN_ID, "description": ""},
            },
            {"id": _LIFECYCLE_ID, "label": "status", "type": "Lifecycle", "properties": {"field_name": "status"}},
            {
                "id": f"{_LIFECYCLE_ID}:draft",
                "label": "draft",
                "type": "StateInitial",
                "properties": {"lifecycle_class_id": "x.Status", "state_key": "draft"},
            },
            {
                "id": f"{_LIFECYCLE_ID}:done",
                "label": "done",
                "type": "StateFinal",
                "properties": {"lifecycle_class_id": "x.Status", "state_key": "done"},
            },
        ],
        "edges": [
            {
                "source_id": _LIFECYCLE_ID,
                "target_id": f"{_LIFECYCLE_ID}:draft",
                "type": "lifecycle_contains_state",
                "relationship": "COMPOSITION",
                "is_dag": False,
                "properties": {"state_key": "draft"},
            },
            {
                "source_id": _LIFECYCLE_ID,
                "target_id": f"{_LIFECYCLE_ID}:done",
                "type": "lifecycle_contains_state",
                "relationship": "COMPOSITION",
                "is_dag": False,
                "properties": {"state_key": "done"},
            },
        ],
    }


def _graph() -> DuckDBGraphResource:
    """Return a freshly built tiny graph."""
    return DuckDBGraphResource.build_from_json(_payload())


def test_the_schema_keeps_no_index_and_no_primary_key() -> None:
    """The catalogue has no explicit index and no primary key, under any name."""
    resource = _graph()

    indexes = resource.execute_fetch_dicts("SELECT index_name FROM duckdb_indexes()")
    keys = resource.execute_fetch_dicts(
        "SELECT constraint_name FROM duckdb_constraints() WHERE constraint_type = 'PRIMARY KEY'",
    )

    assert indexes == [], f"the build created indexes: {indexes}"
    assert keys == [], f"the build created primary keys: {keys}"


def test_the_built_graph_stays_under_the_memory_ceiling() -> None:
    """The total `duckdb_memory()` stays at or under 1.75 MiB, midway between the two variants.

    The ceiling is an absolute MiB figure measured on macOS with the locked DuckDB, and this
    test runs only in the local check run: CI does not run pytest. The shape test above catches
    a single index, including the two `state` indexes that cost about 0.08 MiB here and would
    stay under this ceiling; this test catches a heavy structure that is not an index.
    """
    resource = _graph()

    rows = resource.execute_fetch_dicts(
        "SELECT memory_usage_bytes FROM duckdb_memory() WHERE memory_usage_bytes > 0",
    )
    total_mib = sum(int(row["memory_usage_bytes"]) for row in rows) / _MIB

    assert total_mib <= _CEILING_MIB, f"the built graph took {total_mib:.2f} MiB, ceiling {_CEILING_MIB} MiB"
