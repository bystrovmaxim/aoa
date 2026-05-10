# packages/aoa-maxitor/src/aoa/maxitor/model/diagrams/actions/list_erd_domain_qualnames_action.py
"""
ListErdDomainQualnamesAction — domain interchange qualnames for client-side ERD.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Return ordered ``BaseDomain`` interchange node ids from the embedded nx graph so
the React shell can fetch per-domain payloads separately. The list is always
derived from the graph; there is no request filter on this action. The wire
``domain_qualnames`` field is validated by a static JSON Schema via
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
    @regular_aspect — sort and emit ``erd_domain_qualnames``
          |
          v
    @summary_aspect — ``Result(domain_qualnames=...)``
"""

from __future__ import annotations

from typing import Any, ClassVar, cast

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
from aoa.maxitor.model.diagrams.diagrams_domain import DiagramsDomain


@meta(
    description="List interchange domain type qualnames for ERD client (diagrams)",
    domain=DiagramsDomain,
)
@check_roles(NoneRole)
@connection(ServiceGraphResource, key=SERVICE_GRAPH_CONNECTION_KEY, description="Interchange nx graph from LoadGraphAction")
class ListErdDomainQualnamesAction(
    BaseAction[ParamsStub, "ListErdDomainQualnamesAction.Result"],
):
    """
    AI-CORE-BEGIN
    ROLE: Emit ``domain_qualnames`` for ERD tab discovery on the client.
    CONTRACT: ``domain_qualnames`` are computed only from ``connections["ServiceGraph"].service``.
    INVARIANTS: Reads the graph only via ``connections["ServiceGraph"].service``; pipeline uses ``@regular_aspect`` state keys then ``@summary_aspect``.
    AI-CORE-END
    """

    class Result(BaseResult):
        json_schema: ClassVar = JsonSchemaValue.define(
            name="ErdDomainQualnamesListJson",
            schema={
                "type": "array",
                "items": {"type": "string"},
                "minItems": 0,
            },
        )

        domain_qualnames: json_schema = Field(
            description="Ordered interchange node ids (BaseDomain full qualnames)",
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

    @regular_aspect("Sort domain rows and derive ordered interchange qualnames")
    @result_instance("erd_domain_qualnames", list, required=True)  # type: ignore[untyped-decorator]
    async def sort_domain_qualnames_aspect(
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
        qualnames = [p[1] for p in pairs]
        return {"erd_domain_qualnames": qualnames}

    @summary_aspect("Resolve domain qualifier list from nx graph")
    async def list_qualnames_summary(
        self,
        _params: ParamsStub,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> ListErdDomainQualnamesAction.Result:
        qualnames = list(cast(list[Any], state["erd_domain_qualnames"]))
        return ListErdDomainQualnamesAction.Result(domain_qualnames=qualnames)
