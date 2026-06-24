# tests/examples/pm4py_validation.py
"""PM4Py smoke validation for OCEL 2.0 JSON written by ``plugin.ocel`` resources."""

from __future__ import annotations

from collections.abc import Set
from pathlib import Path
from typing import Any

import pytest

pm4py = pytest.importorskip("pm4py")


def load_ocel2_pm4py(path: Path) -> Any:
    """Load an OCEL 2.0 JSON file through PM4Py."""
    return pm4py.read.read_ocel2_json(str(path))


def assert_ocel2_pm4py_smoke(
    path: Path,
    *,
    expected_event_count: int,
    expected_object_count: int,
    expected_qualifiers: Set[str] | None = None,
    expected_event_id: str | None = None,
) -> None:
    """Assert PM4Py ingests export and core OCEL 2.0 invariants hold."""
    ocel = load_ocel2_pm4py(path)
    assert ocel.is_ocel20()

    events = ocel.events
    objects = ocel.objects
    relations = ocel.relations

    assert len(events) == expected_event_count
    assert len(objects) == expected_object_count

    assert events["ocel:eid"].is_unique, "duplicate event ids in PM4Py view"
    assert objects["ocel:oid"].is_unique, "duplicate object ids in PM4Py view"

    assert events["ocel:activity"].notna().all(), "event type (activity) must be set"
    assert objects["ocel:type"].notna().all(), "object types must be set"

    if expected_event_id is not None:
        assert set(events["ocel:eid"]) == {expected_event_id}

    if expected_qualifiers is not None:
        actual_qualifiers = set(relations["ocel:qualifier"])
        assert actual_qualifiers == set(expected_qualifiers)
        assert len(relations) == len(expected_qualifiers)


def assert_ocel2_pm4py_log(
    path: Path,
    *,
    expected_event_count: int,
    expected_object_count: int | None = None,
    min_object_count: int | None = None,
    min_event_types: int = 1,
    min_object_types: int = 1,
    check_relations_per_event: bool = True,
) -> None:
    """Assert a multi-event OCEL 2.0 log loads in PM4Py with expected cardinality."""
    ocel = load_ocel2_pm4py(path)
    assert ocel.is_ocel20()

    events = ocel.events
    objects = ocel.objects

    assert len(events) == expected_event_count

    if expected_object_count is not None:
        assert len(objects) == expected_object_count
    if min_object_count is not None:
        assert len(objects) >= min_object_count

    assert events["ocel:eid"].is_unique, "duplicate event ids in PM4Py view"
    assert objects["ocel:oid"].is_unique, "duplicate object ids in PM4Py view"

    assert events["ocel:activity"].notna().all()
    assert objects["ocel:type"].notna().all()

    assert events["ocel:activity"].nunique() >= min_event_types
    assert objects["ocel:type"].nunique() >= min_object_types

    if check_relations_per_event:
        assert len(ocel.relations) == expected_event_count * 2, "expected two E2O rows per event"
