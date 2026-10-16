# packages/aoa-maxitor/src/aoa/maxitor/api/duckdb_graph_holder.py
"""
DuckDBGraphHolder — the loaded coordinator graph as one application-scoped resource.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Maxitor's six diagram routes all read one in-process DuckDB snapshot of the coordinator
graph. That snapshot is built by ``POST /api/load`` and kept in
``FastAPI.state.duckdb_graph``; it is one shared object, not one per request. The holder
below declares it the way it actually is — a ready ``BaseResource``, mode 1 — in place of
a per-call factory that handed back the same shared slot while claiming to create a fresh
resource on every call.

The holder is built once, while the application is built, and resolves whatever is loaded
at the moment it is read. It never keeps a graph of its own: a graph stored at build time
would answer from a snapshot a later reload had already replaced.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    POST /api/load ──► FastAPI.state.duckdb_graph ──► DuckDBGraphHolder._resolve()
                                                              │
                                    ┌─────────────────────────┴─────────────────────────┐
                                    ▼                                                   ▼
                              .service                                    .execute_fetch_dicts()
                                    │                                                   │
                                    ▼                                                   ▼
                      DuckDBGraphResource.service                 DuckDBGraphResource.execute_fetch_dicts()

Only the two operations the diagram routes actually use are delegated, and they are
delegated explicitly: nothing is forwarded to the resolved graph, so the holder cannot
quietly grow a surface the routes never asked for. The holder owns no lifecycle — there
is no connection of its own to open or close — so ``get_wrapper_class`` answers ``None``
and the machine passes the same object through to nested actions, unwrapped.
"""

from __future__ import annotations

from typing import Any

import duckdb
from fastapi import FastAPI

from aoa.action_machine.exceptions import HandleError
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.maxitor.model.diagrams.diagrams_domain import DiagramsDomain
from aoa.maxitor.model.diagrams.resources.duckdb_graph_resource import DuckDBGraphResource


@meta(
    description="Application-scoped holder for the loaded coordinator graph",
    domain=DiagramsDomain,
)
class DuckDBGraphHolder(BaseResource):
    """
    AI-CORE-BEGIN
    ROLE: The one shared resource standing for the coordinator graph the application has loaded.
    CONTRACT: ``service`` and ``execute_fetch_dicts`` resolve the graph loaded at the moment of the read.
    INVARIANTS: One per application; holds the application, never a graph; owns no lifecycle.
    AI-CORE-END
    """

    def __init__(self, app: FastAPI) -> None:
        """Keep the application whose loaded graph this holder stands for."""
        self._app = app

    def get_wrapper_class(self) -> type[BaseResource] | None:
        """Return ``None``: there is no lifecycle to protect, so nested actions see this object itself."""
        return None

    async def check_rollup_support(self) -> bool:
        """Report that an in-memory, read-only graph is not a rollup target."""
        return False

    @property
    def service(self) -> duckdb.DuckDBPyConnection:
        """Return the loaded graph's DuckDB connection, read at the moment of the call."""
        return self._resolve().service

    def execute_fetch_dicts(
        self,
        sql: str,
        parameters: list[Any] | tuple[Any, ...] | None = None,
    ) -> list[dict[str, Any]]:
        """Run ``sql`` against the loaded graph and return every row as a column-name to value dictionary."""
        return self._resolve().execute_fetch_dicts(sql, parameters)

    def _resolve(self) -> DuckDBGraphResource:
        """Return the graph loaded in this holder's own application, or refuse when nothing is loaded."""
        graph: DuckDBGraphResource | None = getattr(self._app.state, "duckdb_graph", None)
        if graph is None:
            raise HandleError("Graph is not loaded: call POST /api/load first.")
        return graph
