# packages/aoa-fastapi-adapter/tests/test_adapter_lifespan.py
"""
The adapter's one lifecycle option: an application's startup and shutdown.

The adapter creates the ``FastAPI`` application, so it is the one place that can
hand the application's own context manager to the framework. What it must not do
is add a lifecycle vocabulary of its own: the option is passed through as it is,
and how long its closing takes is the framework's business.

These tests drive the real application object with ``TestClient``, which runs the
lifespan on entering the client and closes it on leaving.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    adapter.build(lifespan=…)  ──>  FastAPI(lifespan=…)
                                        │
                            TestClient ─┴─> startup on enter, closing on exit

"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from aoa.action_machine.context.context import Context
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.fastapi.adapter import FastApiAdapter


def _make_adapter() -> FastApiAdapter:
    """Build the smallest adapter that can produce an application."""
    machine = ActionProductMachine(loggers=[])
    auth = AsyncMock()
    auth.process.return_value = Context()
    return FastApiAdapter(machine=machine, auth_coordinator=auth)


def test_lifespan_runs_at_startup_and_closes_at_shutdown() -> None:
    """The option's context manager is entered while starting and left while stopping."""
    events: list[str] = []

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        events.append("started")
        try:
            yield
        finally:
            events.append("closed")

    app = _make_adapter().build(lifespan=lifespan)

    with TestClient(app) as client:
        assert events == ["started"]
        assert client.get("/health").status_code == 200

    assert events == ["started", "closed"]


def test_a_startup_failure_reaches_the_caller_and_still_closes() -> None:
    """A failing startup is not swallowed into a response, and the closing still runs."""
    events: list[str] = []

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        events.append("started")
        try:
            raise RuntimeError("startup failed")
        finally:
            events.append("closed")
        yield  # never reached: the startup above always fails

    app = _make_adapter().build(lifespan=lifespan)

    with pytest.raises(RuntimeError, match="startup failed"):
        with TestClient(app):
            pass

    assert events == ["started", "closed"]


def test_build_without_the_option_is_unchanged() -> None:
    """Building with no lifecycle option keeps the application exactly as it was."""
    app = _make_adapter().build()

    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
