# packages/aoa-maxitor/src/aoa/maxitor/model/diagrams/actions/list_erd_domain_qualnames_action.py
"""
ListErdDomainQualnamesAction — domain interchange qualnames for client-side ERD.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Return ordered ``BaseDomain`` interchange node ids from the embedded nx graph so
the React shell can fetch per-domain payloads separately. The list is always
derived from the graph; there is no request filter on this action.
"""

from __future__ import annotations

from typing import cast

from pydantic import ConfigDict, Field

from aoa.action_machine.auth import NoneRole
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.connection import connection
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseResult, BaseState, ParamsStub
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.runtime.tools_box import ToolsBox
from aoa.maxitor.api.resources.maxitor_interchange_nx_resource import MaxitorInterchangeNxResource
from aoa.maxitor.model.diagrams.actions.build_erd_graph_data_action import domain_qualnames_from_interchange_nx
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
        domain_qualnames: list[str] = Field(
            default_factory=list,
            description="Ordered interchange node ids (BaseDomain full qualnames)",
        )

        model_config = ConfigDict(arbitrary_types_allowed=True)

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
        return ListErdDomainQualnamesAction.Result(
            domain_qualnames=domain_qualnames_from_interchange_nx(nx_graph),
        )
