# packages/maxitor/front/tests/history_fixtures.py
"""Fixtures of the history tests: the stand-in port, and Maxitor built with it as its own port for public links."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from maxitor.front.api.app import create_app

from tests.fixtures.stand_in_port import StandInPort, stand_in_port


@pytest.fixture
def port() -> Iterator[StandInPort]:
    """A fresh stand-in port with histories of every mode."""
    with stand_in_port() as served:
        yield served


@pytest.fixture
def maxitor(port: StandInPort, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """Maxitor with the stand-in as its own port for public links, its lifespan running."""
    monkeypatch.setenv("MAXITOR_PUBLIC_PORT", port.base)
    with TestClient(create_app()) as client:
        yield client


def open_history(maxitor: TestClient, port: StandInPort, history: str) -> Any:
    """Open a private history of the stand-in as the browser does: its name in the query, its key in the header."""
    return maxitor.get("/api/history/open", params={"history": port.name(history)}, headers={"X-Maxitor-History-Key": port.histories[history].key})
