# packages/maxitor/front/tests/test_map_reads.py
"""The map's two reads (spec 040, FR-010, FR-014): guarded like any read, and a stored version needs no graph built."""

from __future__ import annotations

import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.fixtures.stand_in_port import StandInPort
from tests.history_fixtures import maxitor, open_history, port  # noqa: F401 — fixtures
from tests.test_map_store import Sfdp


@pytest.fixture(autouse=True)
def map_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Keep the maps of this test in its own folder."""
    monkeypatch.setenv("MAXITOR_MAP_CACHE", str(tmp_path))
    yield


def _read(maxitor: TestClient, port: StandInPort, path: str, key: str | None = None, **query: Any) -> Any:  # noqa: F811
    """A read as the browser makes it: the key in the header."""
    return maxitor.get(f"/api/v1/map/{path}", params=query, headers={"X-Maxitor-History-Key": key if key is not None else port.histories["live"].key})


def _version(maxitor: TestClient, port: StandInPort) -> str:  # noqa: F811
    """The source of the newest version of the ``live`` history, with the store's ``sfdp`` stood in."""
    maxitor.app.state.maps._run = Sfdp()  # type: ignore[attr-defined]
    return open_history(maxitor, port, "live").json()["versions"][-1]["source"]


def _ready(maxitor: TestClient, port: StandInPort, source: str) -> dict[str, Any]:  # noqa: F811
    """Read the overview until the map is made."""
    for _ in range(300):
        answer = _read(maxitor, port, "overview", source=source)
        assert answer.status_code == 200, answer.text
        if answer.json()["state"] == "ready":
            return answer.json()
        time.sleep(0.02)
    raise AssertionError("the map was never ready")


def test_the_overview_comes_ready_after_laying_out(maxitor: TestClient, port: StandInPort) -> None:  # noqa: F811
    source = _version(maxitor, port)
    assert _read(maxitor, port, "overview", source=source).json()["state"] == "laying-out"
    overview = _ready(maxitor, port, source)
    assert overview["areas"] and all({"id", "name", "colour", "x", "y", "radius", "counts", "sketch"} <= set(area) for area in overview["areas"])


def test_an_area_reads_up_to_its_level(maxitor: TestClient, port: StandInPort) -> None:  # noqa: F811
    source = _version(maxitor, port)
    area = max(_ready(maxitor, port, source)["areas"], key=lambda item: sum(item["counts"].values()))
    near = _read(maxitor, port, "area", source=source, id=area["id"], level=3).json()
    far = _read(maxitor, port, "area", source=source, id=area["id"], level=2).json()
    assert {item["level"] for item in far["nodes"]} <= {2}
    assert len(near["nodes"]) == sum(area["counts"].values())
    assert len(far["nodes"]) < len(near["nodes"])


def test_an_unknown_area_is_not_found(maxitor: TestClient, port: StandInPort) -> None:  # noqa: F811
    source = _version(maxitor, port)
    _ready(maxitor, port, source)
    assert _read(maxitor, port, "area", source=source, id="nowhere", level=2).status_code == 404


def test_a_wrong_key_reads_not_found(maxitor: TestClient, port: StandInPort) -> None:  # noqa: F811
    source = _version(maxitor, port)
    _ready(maxitor, port, source)
    assert _read(maxitor, port, "overview", key="wrong", source=source).status_code == 404


def test_a_stored_version_is_read_with_no_graph_built(maxitor: TestClient, port: StandInPort) -> None:  # noqa: F811
    source = _version(maxitor, port)
    expected = _ready(maxitor, port, source)
    store = maxitor.app.state.graph_store  # type: ignore[attr-defined]
    store.acquire = None
    assert _read(maxitor, port, "overview", source=source).json() == expected
