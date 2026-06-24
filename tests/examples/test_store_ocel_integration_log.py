# packages/aoa-examples/aoa_examples_tests/test_store_ocel_integration_log.py
"""Integration — batch storefront OCEL export to ``archive/logs/ocel.json``."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aoa.examples.model.store.ocel_export import build_store_ocel_machine, run_store_ocel_trace_batch
from tests.ocel.pm4py_validation import assert_ocel2_pm4py_log, load_ocel2_pm4py

REPO_ROOT = Path(__file__).resolve().parents[3]
ARCHIVE_OCEL_PATH = REPO_ROOT / "archive/logs/ocel.json"
ARCHIVE_TRACE_COUNT = 30
OCPM_UPLOAD_URL = "https://www.ocpm.info/ocel.html"
MIN_EVENT_TYPES = 5
MIN_OBJECT_TYPES = 9
MIN_OBJECT_COUNT = 50


def _print_ocel_json_summary(path: Path) -> None:
    """Print JSON shape for manual inspection (use ``pytest -s``)."""
    doc = json.loads(path.read_text(encoding="utf-8"))
    print("JSON top-level keys:", sorted(doc))
    print("  events:", len(doc["events"]))
    print("  objects:", len(doc["objects"]))
    print("  eventTypes:", len(doc["eventTypes"]))
    print("  objectTypes:", len(doc["objectTypes"]))
    if doc["events"]:
        print("  sample event id:", doc["events"][0]["id"])
        print("  sample qualifiers:", [r["qualifier"] for r in doc["events"][0]["relationships"]])
    print("eventTypes", [entry["name"] for entry in doc["eventTypes"]])
    print("objectTypes", [entry["name"] for entry in doc["objectTypes"]])


def _print_pm4py_compatibility_report(path: Path, *, trace_count: int) -> None:
    """PM4Py OCEL 2.0 read + summary on stdout (use ``pytest -s``)."""
    assert_ocel2_pm4py_log(
        path,
        expected_event_count=trace_count,
        min_object_count=MIN_OBJECT_COUNT,
        min_event_types=MIN_EVENT_TYPES,
        min_object_types=MIN_OBJECT_TYPES,
        check_relations_per_event=False,
    )
    ocel = load_ocel2_pm4py(path)
    print("is_ocel20:", ocel.is_ocel20())
    print(ocel.get_summary())
    print("activities:", ocel.events["ocel:activity"].value_counts().to_dict())
    print("object types:", ocel.objects["ocel:type"].value_counts().to_dict())
    print("qualifiers:", sorted(ocel.relations["ocel:qualifier"].unique()))
    print("PM4Py read_ocel2_json: OK")


def _require_archive_ocel_log() -> Path:
    if not ARCHIVE_OCEL_PATH.is_file():
        pytest.skip(
            f"missing {ARCHIVE_OCEL_PATH} — run test_write_archive_ocel_log_for_ocpm first",
        )
    return ARCHIVE_OCEL_PATH


@pytest.mark.integration
@pytest.mark.parametrize("trace_count", [20, 30, 50])
@pytest.mark.asyncio
async def test_store_ocel_lifecycle_batch(tmp_path: Path, trace_count: int) -> None:
    output = tmp_path / f"store-ocel-{trace_count}.json"
    machine, store = build_store_ocel_machine(output)

    executed = await run_store_ocel_trace_batch(machine, store, trace_count=trace_count)
    assert executed == trace_count
    assert output.exists()

    assert_ocel2_pm4py_log(
        output,
        expected_event_count=trace_count,
        min_object_count=max(MIN_OBJECT_COUNT * trace_count // ARCHIVE_TRACE_COUNT, MIN_OBJECT_TYPES),
        min_event_types=MIN_EVENT_TYPES,
        min_object_types=MIN_OBJECT_TYPES,
        check_relations_per_event=False,
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_write_archive_ocel_log_for_ocpm() -> None:
    """Persist ``archive/logs/ocel.json`` for manual upload to ocpm.info."""
    ARCHIVE_OCEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    machine, store = build_store_ocel_machine(ARCHIVE_OCEL_PATH)

    executed = await run_store_ocel_trace_batch(
        machine,
        store,
        trace_count=ARCHIVE_TRACE_COUNT,
    )
    assert executed == ARCHIVE_TRACE_COUNT
    assert ARCHIVE_OCEL_PATH.is_file()

    assert_ocel2_pm4py_log(
        ARCHIVE_OCEL_PATH,
        expected_event_count=ARCHIVE_TRACE_COUNT,
        min_object_count=MIN_OBJECT_COUNT,
        min_event_types=MIN_EVENT_TYPES,
        min_object_types=MIN_OBJECT_TYPES,
        check_relations_per_event=False,
    )

    doc = json.loads(ARCHIVE_OCEL_PATH.read_text(encoding="utf-8"))
    assert set(doc) == {"eventTypes", "objectTypes", "events", "objects"}
    assert len(doc["events"]) == ARCHIVE_TRACE_COUNT
    assert len(doc["eventTypes"]) >= MIN_EVENT_TYPES
    assert len(doc["objectTypes"]) >= MIN_OBJECT_TYPES
    event_type_names = {entry["name"] for entry in doc["eventTypes"]}
    object_type_names = {entry["name"] for entry in doc["objectTypes"]}
    assert "PublishOrderCreatedOcel" in event_type_names
    assert "SalesOrder" in object_type_names
    assert all("." not in name for name in event_type_names)
    assert all("." not in name for name in object_type_names)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_store_ocel_verbose_archive_run() -> None:
    """Per-action console log, JSON stats, PM4Py summary → ``archive/logs/ocel.json``."""
    ARCHIVE_OCEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    machine, store = build_store_ocel_machine(ARCHIVE_OCEL_PATH)
    executed = await run_store_ocel_trace_batch(
        machine,
        store,
        trace_count=ARCHIVE_TRACE_COUNT,
        verbose=True,
        output_file=ARCHIVE_OCEL_PATH,
    )
    assert executed == ARCHIVE_TRACE_COUNT
    assert ARCHIVE_OCEL_PATH.is_file()

    _print_ocel_json_summary(ARCHIVE_OCEL_PATH)
    _print_pm4py_compatibility_report(ARCHIVE_OCEL_PATH, trace_count=ARCHIVE_TRACE_COUNT)
    print(f"\nUpload: {OCPM_UPLOAD_URL}  ←  {ARCHIVE_OCEL_PATH}")


@pytest.mark.integration
def test_inspect_archive_ocel_json() -> None:
    """Print JSON counts and types for the archive artefact."""
    path = _require_archive_ocel_log()
    _print_ocel_json_summary(path)

    doc = json.loads(path.read_text(encoding="utf-8"))
    assert set(doc) == {"eventTypes", "objectTypes", "events", "objects"}
    assert len(doc["events"]) == ARCHIVE_TRACE_COUNT
    assert len(doc["objects"]) >= MIN_OBJECT_COUNT
    assert len(doc["eventTypes"]) >= MIN_EVENT_TYPES
    assert len(doc["objectTypes"]) >= MIN_OBJECT_TYPES


@pytest.mark.integration
def test_archive_ocel_pm4py_compatibility() -> None:
    """PM4Py OCEL 2.0 schema check on ``archive/logs/ocel.json``."""
    path = _require_archive_ocel_log()
    _print_pm4py_compatibility_report(path, trace_count=ARCHIVE_TRACE_COUNT)
