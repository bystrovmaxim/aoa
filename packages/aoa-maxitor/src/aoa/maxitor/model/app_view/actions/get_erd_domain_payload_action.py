# packages/aoa-maxitor/src/aoa/maxitor/model/app_view/actions/get_erd_domain_payload_action.py
"""
GetErdDomainPayloadAction — one bounded-context ERD graph as JSON for the client.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Materialize ``{nodes, edges}`` for a single ``domain_qualname`` so the SPA can
render ERD without server-generated HTML.
"""

from __future__ import annotations

from typing import Any, cast

from pydantic import ConfigDict, Field

from aoa.action_machine.auth import NoneRole
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.connection import connection
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult, BaseState
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.runtime.tools_box import ToolsBox
from aoa.maxitor.api.resources.maxitor_interchange_nx_resource import MaxitorInterchangeNxResource
from aoa.maxitor.model.app_view.actions.build_erd_graph_data_action import (
    erd_payload_from_coordinator_for_domain,
    node_graph_coordinator_from_interchange_nx,
    payload_to_domain_dict,
)
from aoa.maxitor.model.app_view.app_view_domen_domain import AppViewDomenDomain

from ._erd_domain_import import import_domain_type_from_qualname


@meta(
    description="Get ERD nodes/edges JSON for one interchange domain qualname (app-view)",
    domain=AppViewDomenDomain,
)
@check_roles(NoneRole)
@connection(MaxitorInterchangeNxResource, key="interchange_nx", description="Interchange nx graph from LoadGraphAction")
class GetErdDomainPayloadAction(
    BaseAction["GetErdDomainPayloadAction.Params", "GetErdDomainPayloadAction.Result"],
):
    """
    AI-CORE-BEGIN
    ROLE: Emit one domain slice of ``ERD_DATA``-shaped JSON for client rendering.
    CONTRACT: ``domain_qualname`` is the full interchange node id for a ``BaseDomain`` class.
    INVARIANTS: Reads ``nx_graph`` only via ``connections[\"interchange_nx\"]``.
    AI-CORE-END
    """

    class Params(BaseParams):
        domain_qualname: str = Field(
            min_length=1,
            description="Full qualname of the BaseDomain interchange node id",
        )

        model_config = ConfigDict(arbitrary_types_allowed=True)

    class Result(BaseResult):
        domain_label: str = Field(description="Human tab label (domain name or class name)")
        domain_qualifier: str = Field(description="Same as request interchange qualname")
        graph: dict[str, Any] = Field(
            description="ERD_DATA-style object: {nodes: [...], edges: [...]}",
        )

        model_config = ConfigDict(arbitrary_types_allowed=True)

    @summary_aspect("Build ERD graph JSON for one domain")
    async def build_domain_payload_summary(
        self,
        params: GetErdDomainPayloadAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> GetErdDomainPayloadAction.Result:
        nx_resource = cast(MaxitorInterchangeNxResource, connections["interchange_nx"])
        coordinator = node_graph_coordinator_from_interchange_nx(nx_resource.nx_graph)
        qual = params.domain_qualname.strip()
        dc = import_domain_type_from_qualname(qual)
        payload = erd_payload_from_coordinator_for_domain(coordinator, dc)
        base = getattr(dc, "name", None) or dc.__name__
        return GetErdDomainPayloadAction.Result(
            domain_label=str(base),
            domain_qualifier=qual,
            graph=payload_to_domain_dict(payload),
        )
