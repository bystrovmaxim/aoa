# packages/maxitor/app/src/maxitor/viewer/api/duckdb_graph_holder.py
"""
DuckDBGraphHolder — the graph read bound to the current request, as one ready resource.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Maxitor's six diagram routes all query an in-process DuckDB snapshot. Since #214 that
snapshot is not one slot shared by every caller: each read names its source
(``?source=<graph-json URL>``), ``GraphSourceMiddleware`` asks the ``GraphStore`` for that
source's entry, and binds it to the request. The holder below is the ``BaseResource`` the
adapters hand to the diagram actions: a ready resource, mode 1, that resolves the entry
bound to the request it is serving.

It keeps nothing of its own. One holder is built per application, but the graph it answers
from belongs to the request: a holder that remembered a graph would answer the next reader
with the previous reader's service, which is exactly the defect #214 removed. Outside a
bound request it refuses by naming the missing binding, not ``POST /api/load``.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    GET /api/v1/…?source=… ──► GraphSourceMiddleware ──► GraphStore.acquire(source)
                                        │                        │
                                        │  binds one entry       │ builds on a cold read
                                        ▼                        ▼
                             ContextVar (this request) ──► GraphEntry
                                                                 │
                                                                 ▼
                                                     DuckDBGraphHolder._resolve()
                                                                 │
                                    ┌────────────────────────────┴────────────────────────────┐
                                    ▼                                                         ▼
                              .service                                            .execute_fetch_dicts()
                                    │                                                         │
                                    ▼                                                         ▼
                      DuckDBGraphResource.service                   DuckDBGraphResource.execute_fetch_dicts()

Only the two operations the diagram routes actually use are delegated, and they are
delegated explicitly: nothing is forwarded to the resolved graph, so the holder cannot
quietly grow a surface the routes never asked for. The holder owns no lifecycle — there is
no connection of its own to open or close — so ``get_wrapper_class`` answers ``None`` and
the machine passes the same object through to nested actions, unwrapped. Removing or
replacing an entry in the store never closes the graph its request is still reading: the
entry lives as long as the request's binding holds a reference to it.
"""

from __future__ import annotations

from typing import Any

import duckdb
from maxitor.viewer.api.graph_source_middleware import current_graph_entry
from maxitor.viewer.model.diagrams.diagrams_domain import DiagramsDomain
from maxitor.viewer.model.diagrams.resources.duckdb_graph_resource import DuckDBGraphResource

from aoa.action_machine.exceptions import HandleError
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.base_resource import BaseResource


@meta(
    description="Request-scoped holder for the graph the current read named",
    domain=DiagramsDomain,
)
class DuckDBGraphHolder(BaseResource):
    """
    AI-CORE-BEGIN
    ROLE: The ready resource standing for the graph the current request named with ``?source=``.
    CONTRACT: ``service`` and ``execute_fetch_dicts`` resolve the graph bound to the read they serve.
    INVARIANTS: One per application; holds no graph of its own; resolves the request's entry, and
    refuses by name when the request was never bound.
    AI-CORE-END
    """

    def get_wrapper_class(self) -> type[BaseResource] | None:
        """Return ``None``: there is no lifecycle to protect, so nested actions see this object itself."""
        return None

    async def check_rollup_support(self) -> bool:
        """Report that an in-memory, read-only graph is not a rollup target."""
        return False

    @property
    def service(self) -> duckdb.DuckDBPyConnection:
        """Return the request's graph connection, read at the moment of the call."""
        return self._resolve().service

    def execute_fetch_dicts(
        self,
        sql: str,
        parameters: list[Any] | tuple[Any, ...] | None = None,
    ) -> list[dict[str, Any]]:
        """Run ``sql`` against the request's graph and return every row as a column-name to value dictionary."""
        return self._resolve().execute_fetch_dicts(sql, parameters)

    def _resolve(self) -> DuckDBGraphResource:
        """Return the graph bound to this request, or refuse by naming the missing binding."""
        entry = current_graph_entry()
        if entry is None:
            raise HandleError(
                "No graph is bound to this request: a diagram read must name its source "
                "in the 'source' query parameter.",
            )
        return entry.graph
