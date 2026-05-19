# packages/aoa-maxitor/src/aoa/maxitor/model/diagrams/actions/list_domains_action.py
"""
ListDomainsAction — domain interchange rows (qualname + colour) for client-side ERD.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Return ordered domain rows (interchange qualname + accent colour) from
``connections["DuckDBGraph"]`` so the React shell can fetch per-domain payloads separately.
Rows are read from the DuckDB ``domain`` table (same coordinator graph load as
``ListEntitiesAction``). Accent colours use ``_LIST_DOMAINS_DISTINCT_COLORS`` by row index
after SQL sort. The wire ``list_domains`` field uses ``ListDomainsJson`` from
:mod:`~aoa.maxitor.model.diagrams.actions.list_domains_action_schema`.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    ``connections["DuckDBGraph"]`` (``domain`` table)
          |
          v
    @summary_aspect — ``Result(list_domains=...)``
"""

from __future__ import annotations

from typing import Any, cast

from pydantic import Field

from aoa.action_machine.auth import NoneRole
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.connection import connection
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseResult, BaseState, ParamsStub
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.runtime.tools_box import ToolsBox
from aoa.maxitor.model.diagrams.actions.list_domains_action_schema import ListDomainsJson
from aoa.maxitor.model.diagrams.diagrams_domain import DiagramsDomain
from aoa.maxitor.model.diagrams.resources.duckdb_graph_resource import (
    DUCKDB_GRAPH_CONNECTION_KEY,
    DuckDBGraphResource,
)

# Ordered palette: React ERD disk hues first, then extra saturated tones; longer domain lists cycle.
_EXTRA_LIST_DOMAIN_COLORS: tuple[str, ...] = (
    "#3b82f6",
    "#8b5cf6",
    "#10b981",
    "#f59e0b",
    "#ef4444",
    "#06b6d4",
    "#ec4899",
    "#64748b",
    "#2563eb",
    "#dc2626",
    "#16a34a",
    "#d97706",
    "#7c3aed",
    "#0891b2",
    "#db2777",
    "#4f46e5",
    "#ea580c",
    "#059669",
    "#a855f7",
    "#0d9488",
    "#e11d48",
    "#65a30d",
    "#c026d3",
    "#0369a1",
    "#b45309",
    "#15803d",
    "#9333ea",
    "#0e7490",
    "#4d7c0f",
    "#b91c1c",
    "#be185d",
    "#4338ca",
)


def _unique_color_tuple(*segments: tuple[str, ...]) -> tuple[str, ...]:
    """Concatenate colour tuples, preserving order and dropping case-insensitive duplicates."""
    seen: set[str] = set()
    out: list[str] = []
    for seg in segments:
        for hex_color in seg:
            key = hex_color.casefold()
            if key in seen:
                continue
            seen.add(key)
            out.append(hex_color)
    return tuple(out)


_LIST_DOMAINS_DISTINCT_COLORS: tuple[str, ...] = _unique_color_tuple(_EXTRA_LIST_DOMAIN_COLORS)


@meta(
    description="List interchange domain type qualnames for ERD client (diagrams)",
    domain=DiagramsDomain,
)
@check_roles(NoneRole)
@connection(
    DuckDBGraphResource,
    key=DUCKDB_GRAPH_CONNECTION_KEY,
    description="Coordinator graph in DuckDB (domain rows for ERD discovery)",
)
class ListDomainsAction(BaseAction[ParamsStub, "ListDomainsAction.Result"]):
    """
    AI-CORE-BEGIN
    ROLE: Emit ``list_domains`` rows (qualname + color) for ERD tab discovery on the client.
    CONTRACT: Domain rows come from DuckDB ``domain`` ordered like the former nx pipeline (label then id); test and ``<locals>`` ids are excluded.
    INVARIANTS: Reads ``connections[DuckDBGraph]`` only — no NetworkX scan.
    AI-CORE-END
    """

    class Result(BaseResult):
        """HTTP/JSON body is ``model_dump(mode="json")`` of this result (single key ``list_domains``)."""

        # [
        #   {"qualname": "aoa.orders.domain.OrdersDomain", "label": "Orders", "color": "#3b82f6"},
        #   {"qualname": "aoa.billing.domain.BillingDomain", "label": "Billing", "color": "#8b5cf6"}
        # ]
        list_domains: ListDomainsJson = Field(
            description="Ordered interchange qualname rows with ERD accent hex colour per row.",
        )

    @staticmethod
    def _list_domains_rows(duck: DuckDBGraphResource) -> list[dict[str, Any]]:
        """Return ``list_domains`` rows: qualnames from DuckDB with cycling accent colours."""
        sql = """
        SELECT id AS qualname, label AS label
        FROM domain
        WHERE id NOT LIKE 'tests.%'
          AND strpos(id, '<locals>') = 0
        ORDER BY lower(label), lower(COALESCE(NULLIF(name, ''), label, id)), id
        """
        raw = duck.execute_fetch_dicts(sql)
        palette = _LIST_DOMAINS_DISTINCT_COLORS
        return [
            {
                "qualname": str(row["qualname"]),
                "label": str(row["label"]),
                "color": palette[i % len(palette)],
            }
            for i, row in enumerate(raw)
        ]

    @staticmethod
    def domain_accent_rows(duck: DuckDBGraphResource) -> list[dict[str, Any]]:
        """Same rows as ``list_domains`` (qualname + ERD accent hex); for other diagrams actions."""
        return ListDomainsAction._list_domains_rows(duck)

    @summary_aspect("Resolve domain qualifier list from DuckDB graph")
    async def build_list_domains_summary(
        self,
        _params: ParamsStub,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> ListDomainsAction.Result:
        duck = cast(DuckDBGraphResource, connections[DUCKDB_GRAPH_CONNECTION_KEY])
        return ListDomainsAction.Result(list_domains=ListDomainsAction.domain_accent_rows(duck))
