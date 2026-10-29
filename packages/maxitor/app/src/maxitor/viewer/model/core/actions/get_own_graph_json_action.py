# packages/maxitor/app/src/maxitor/viewer/model/core/actions/get_own_graph_json_action.py
"""
GetOwnGraphJsonAction — Maxitor serves its own model as graph-json.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``GET /examples/model/graph-json`` answers with Maxitor's own model in the shape every
AOA service uses (``{"coordinator_json": …}``), at the path Maxitor adds to a bare
address — so its own address opens its own diagram (spec 029, FR-060). The adapter tags
the answer with an ``ETag`` and answers ``304`` to a request that names it (FR-061).

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    GET /examples/model/graph-json ──► GetOwnGraphJsonAction
                                          └─ connections["OwnModelGraph"].graph_json()
"""

from __future__ import annotations

from typing import cast

from maxitor.viewer.model.core.core_domain import CoreDomain
from maxitor.viewer.model.core.resources.own_model_graph_resource import (
    OWN_MODEL_GRAPH_CONNECTION_KEY,
    OwnModelGraphResource,
)
from pydantic import Field

from aoa.action_machine.auth import GuestRole
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.connection import connection
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseResult, BaseState, ParamsStub
from aoa.action_machine.resources import Connections
from aoa.action_machine.runtime.tools_box import ToolsBox


class OwnGraphJsonResult(BaseResult):
    """Maxitor's own model, as an AOA service's graph-json."""

    coordinator_json: str = Field(description="Interchange export of Maxitor's own coordinator.")


@meta(description="Serve Maxitor's own model as graph-json", domain=CoreDomain)
@check_roles(GuestRole)
@connection(OwnModelGraphResource, key=OWN_MODEL_GRAPH_CONNECTION_KEY, description="Maxitor's own model")
class GetOwnGraphJsonAction(BaseAction[ParamsStub, OwnGraphJsonResult]):
    """
    AI-CORE-BEGIN
    ROLE: Answer with Maxitor's own model, so Maxitor can be opened as a service like any other.
    CONTRACT: ``coordinator_json`` is the interchange JSON of the coordinator Maxitor's machine was built with.
    INVARIANTS: Reads only.
    AI-CORE-END
    """

    @summary_aspect("Read Maxitor's own model")
    async def own_graph_json_summary(
        self,
        params: ParamsStub,
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
    ) -> OwnGraphJsonResult:
        """Return the interchange JSON of Maxitor's own model."""
        model = cast(OwnModelGraphResource, connections[OWN_MODEL_GRAPH_CONNECTION_KEY])
        return OwnGraphJsonResult(coordinator_json=model.graph_json())
