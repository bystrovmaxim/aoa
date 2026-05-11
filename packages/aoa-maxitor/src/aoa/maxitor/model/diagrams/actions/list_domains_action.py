# packages/aoa-maxitor/src/aoa/maxitor/model/diagrams/actions/list_domains_action.py
"""
ListDomainsAction — domain interchange rows (qualname + colour) for client-side ERD.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Return ordered domain rows (interchange qualname + accent colour) from the embedded
nx graph so the React shell can fetch per-domain payloads separately. The list is always
derived from the graph; there is no request filter on this action. The first twenty
domain rows receive pairwise distinct accent hex colours (legacy ``ERD_DEFAULT_ENTITY_COLORS``
first, then additional hues); further rows cycle within the combined palette. The wire ``list_domains`` field uses the module-level ``ListDomainsJson`` type from
:class:`~aoa.action_machine.model.json_schema_value.JsonSchemaValue`.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    ``connections["ServiceGraph"].service`` (NetworkX ``DiGraph``)
          |
          v
    @regular_aspect — collect ``[label, qualname]`` rows (``erd_domain_label_rows``)
          |
          v
    @regular_aspect — sort and emit ``erd_domain_infos`` (qualname + color)
          |
          v
    @summary_aspect — ``Result(list_domains=...)``
"""

from __future__ import annotations

from typing import Any, cast

from pydantic import Field

from aoa.action_machine.auth import NoneRole
from aoa.action_machine.graph_model.nodes.domain_graph_node import DomainGraphNode
from aoa.action_machine.intents.aspects import regular_aspect, summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.checkers import result_instance
from aoa.action_machine.intents.connection import connection
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseResult, BaseState, JsonSchemaValue, ParamsStub
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.runtime.tools_box import ToolsBox
from aoa.maxitor.model.core.resources.service_graph_resource import (
    SERVICE_GRAPH_CONNECTION_KEY,
    ServiceGraphResource,
)
from aoa.maxitor.model.diagrams.actions.build_erd_graph_data_action import ERD_DEFAULT_ENTITY_COLORS
from aoa.maxitor.model.diagrams.diagrams_domain import DiagramsDomain

# Legacy entity-disk palette first (same order as ``ERD_DEFAULT_ENTITY_COLORS``), then extra
# saturated hues so the first twenty domain rows stay visually distinct; longer lists cycle.
_EXTRA_LIST_DOMAIN_COLORS: tuple[str, ...] = (
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


_LIST_DOMAINS_DISTINCT_COLORS: tuple[str, ...] = _unique_color_tuple(
    ERD_DEFAULT_ENTITY_COLORS,
    _EXTRA_LIST_DOMAIN_COLORS,
)

# Ordered interchange ``BaseDomain`` type qualnames with one ERD accent hex per row; used for
# ``ListDomainsAction.Result.list_domains`` and the domain-qualnames HTTP JSON body.
ListDomainsJson = JsonSchemaValue.define(
    name="ListDomainsJson",
    schema={
        "type": "array",
        "minItems": 0,
        "items": {
            "type": "object",
            "properties": {
                "qualname": {"type": "string"},
                "color": {"type": "string"},
            },
            "required": ["qualname", "color"],
            "additionalProperties": False,
        },
    },
)


@meta(
    description="List interchange domain type qualnames for ERD client (diagrams)",
    domain=DiagramsDomain,
)
@check_roles(NoneRole)
@connection(ServiceGraphResource, key=SERVICE_GRAPH_CONNECTION_KEY, description="Interchange nx graph from LoadGraphAction")
class ListDomainsAction(
    BaseAction[ParamsStub, "ListDomainsAction.Result"],
):
    """
    AI-CORE-BEGIN
    ROLE: Emit ``list_domains`` rows (qualname + color) for ERD tab discovery on the client.
    CONTRACT: Domain rows are computed only from ``connections["ServiceGraph"].service``; colours use ``_LIST_DOMAINS_DISTINCT_COLORS`` by sorted index (first twenty unique).
    INVARIANTS: Reads the graph only via ``connections["ServiceGraph"].service``; pipeline uses ``@regular_aspect`` state keys then ``@summary_aspect``.
    AI-CORE-END
    """

    class Result(BaseResult):
        """HTTP/JSON body is ``model_dump(mode="json")`` of this result (single key ``list_domains``)."""

        # [
        #   {"qualname": "aoa.orders.domain.OrdersDomain", "color": "#3b82f6"},
        #   {"qualname": "aoa.billing.domain.BillingDomain", "color": "#8b5cf6"}
        # ]
        list_domains: ListDomainsJson = Field(
            description="Ordered interchange qualname rows with ERD accent hex colour per row.",
        )

    @regular_aspect("Collect domain interchange label rows from nx graph")
    @result_instance("erd_domain_label_rows", list, required=True)  # type: ignore[untyped-decorator]
    async def collect_domain_label_rows_aspect(
        self,
        _params: ParamsStub,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> dict[str, Any]:
        nx_resource = cast(ServiceGraphResource, connections[SERVICE_GRAPH_CONNECTION_KEY])
        rows: list[list[str]] = []
        for nid, data in nx_resource.service.nodes(data=True):
            if str(data.get("node_type", "")) != DomainGraphNode.NODE_TYPE:
                continue
            nid_s = str(nid)
            if nid_s.startswith("tests.") or "<locals>" in nid_s:
                continue
            label = str(data.get("label", ""))
            rows.append([label, nid_s])
        return {"erd_domain_label_rows": rows}

    @regular_aspect("Sort domain rows and attach distinct ERD accent colours")
    @result_instance("erd_domain_infos", list, required=True)  # type: ignore[untyped-decorator]
    async def sort_domain_infos_aspect(
        self,
        _params: ParamsStub,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> dict[str, Any]:
        raw_rows = cast(list[Any], state["erd_domain_label_rows"])
        pairs: list[tuple[str, str]] = []
        for pair in raw_rows:
            pairs.append((str(pair[0]), str(pair[1])))
        pairs.sort(key=lambda lr: (lr[0].lower(), lr[1]))
        palette = _LIST_DOMAINS_DISTINCT_COLORS
        infos = [
            {"qualname": qual, "color": palette[i % len(palette)]}
            for i, (_label, qual) in enumerate(pairs)
        ]
        return {"erd_domain_infos": infos}

    @summary_aspect("Resolve domain qualifier list from nx graph")
    async def list_qualnames_summary(
        self,
        _params: ParamsStub,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> ListDomainsAction.Result:
        infos = list(cast(list[Any], state["erd_domain_infos"]))
        return ListDomainsAction.Result(list_domains=infos)
