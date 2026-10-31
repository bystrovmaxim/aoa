# packages/maxitor/front/src/maxitor/front/model/diagrams/actions/all_use_cases_diagram_action.py
"""
GetAllUseCasesDiagramAction — every role and every use case on one diagram.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The whole application's answer to "who can do what" (spec 041): the same diagram as one
domain's, over all of them, for the left panel's *Use case all domains view*.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    GET /api/v1/use-case-diagram ──► DuckDB ──► use_case_diagram(duck, None)
"""

from __future__ import annotations

from typing import cast

from maxitor.front.model.diagrams.actions.domain_use_case_diagram_action import use_case_diagram
from maxitor.front.model.diagrams.actions.domain_use_case_diagram_action_schema import DomainUseCaseDiagramJson
from maxitor.front.model.diagrams.diagrams_domain import DiagramsDomain
from maxitor.front.model.diagrams.resources.duckdb_graph_resource import (
    DUCKDB_GRAPH_CONNECTION_KEY,
    DuckDBGraphResource,
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


class AllUseCasesResult(BaseResult):
    """The diagram of every domain."""

    domain_use_case_diagram: DomainUseCaseDiagramJson = Field(description="All actions, all roles and typed edges for use-case rendering.")


@meta(description="Return the use-case diagram of every domain together", domain=DiagramsDomain)
@check_roles(GuestRole)
@connection(DuckDBGraphResource, key=DUCKDB_GRAPH_CONNECTION_KEY, description="Coordinator graph in DuckDB")
class GetAllUseCasesDiagramAction(BaseAction[ParamsStub, AllUseCasesResult]):
    """
    AI-CORE-BEGIN
    ROLE: Materialize the whole application's use-case graph for SPA / Graphviz.
    CONTRACT: The shape of one domain's diagram, its ``domain`` naming all of them.
    AI-CORE-END
    """

    @summary_aspect("Build the use-case diagram of every domain")
    async def all_use_cases_summary(
        self,
        params: ParamsStub,
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
    ) -> AllUseCasesResult:
        """Build the diagram with no domain to narrow it."""
        _ = (params, state, box)
        duck = cast(DuckDBGraphResource, connections[DUCKDB_GRAPH_CONNECTION_KEY])
        return AllUseCasesResult(domain_use_case_diagram=use_case_diagram(duck, None))
