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
"""

from __future__ import annotations

from typing import ClassVar, cast

from pydantic import Field

from aoa.action_machine.auth import NoneRole
from aoa.action_machine.graph_model.nodes.domain_graph_node import DomainGraphNode
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.connection import connection
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseResult, BaseState, JsonSchemaValue, ParamsStub
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.runtime.tools_box import ToolsBox
from aoa.maxitor.api.resources.maxitor_interchange_nx_resource import MaxitorInterchangeNxResource
from aoa.maxitor.model.diagrams.diagrams_domain import DiagramsDomain


@meta(
    description="List interchange domain type qualnames for ERD client (diagrams)",
    domain=DiagramsDomain,
)
@check_roles(NoneRole)
@connection(MaxitorInterchangeNxResource, key="interchange_nx", description="Interchange nx graph from LoadGraphAction")
class ListErdDomainQualnamesAction(
    BaseAction[ParamsStub, "ListErdDomainQualnamesAction.Result"],
):
    """
    AI-CORE-BEGIN
    ROLE: Emit ``domain_qualnames`` for ERD tab discovery on the client.
    CONTRACT: ``domain_qualnames`` are computed only from ``connections[\"interchange_nx\"].nx_graph``.
    INVARIANTS: Reads ``nx_graph`` only via ``connections[\"interchange_nx\"]``.
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

    @summary_aspect("Resolve domain qualifier list from nx graph")
    async def list_qualnames_summary(
        self,
        _params: ParamsStub,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> ListErdDomainQualnamesAction.Result:
        nx_resource = cast(MaxitorInterchangeNxResource, connections["interchange_nx"])
        nx_graph = nx_resource.nx_graph
        rows: list[tuple[str, str]] = []
        for nid, data in nx_graph.nodes(data=True):
            if str(data.get("node_type", "")) != DomainGraphNode.NODE_TYPE:
                continue
            nid_s = str(nid)
            if nid_s.startswith("tests.") or "<locals>" in nid_s:
                continue
            label = str(data.get("label", ""))
            rows.append((label, nid_s))
        rows.sort(key=lambda lr: (lr[0].lower(), lr[1]))
        return ListErdDomainQualnamesAction.Result(
            domain_qualnames=[r[1] for r in rows],
        )
