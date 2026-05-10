# packages/aoa-maxitor/src/aoa/maxitor/api/session.py
"""
MaxitorApiSession — shared ActionMachine state for FastAPI routes.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Build the demo interchange coordinator once, then expose the NetworkX graph,
sidebar rows, and shared :class:`ActionProductMachine` to request handlers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import networkx as nx

from aoa.action_machine.context.context import Context
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.graph.node_graph_coordinator import NodeGraphCoordinator
from aoa.maxitor.model.app_view.actions.get_left_menu_sidebar_data_action import GetLeftMenuSidebarDataAction
from aoa.maxitor.model.core.actions.load_graph_action import LoadGraphAction
from aoa.maxitor.samples.interchange_demo_coordinator import (
    build_registered_interchange_coordinator,
    import_sample_registration_modules,
)


@dataclass(frozen=True)
class MaxitorApiSession:
    """
    AI-CORE-BEGIN
    ROLE: Immutable runtime state for one FastAPI application process.
    CONTRACT: Holds the single action machine used to materialize graph, sidebar, and ERD data.
    INVARIANTS: Request handlers reuse these objects; they must not create fresh default machines.
    AI-CORE-END
    """

    sidebar_data: Any
    nx_graph: nx.DiGraph[Any]
    coordinator: NodeGraphCoordinator
    action_machine: ActionProductMachine


async def build_maxitor_api_session(*, machine: ActionProductMachine) -> MaxitorApiSession:
    """
    Load coordinator graph -> NetworkX + sidebar rows for the FastAPI app.

    AI-CORE-BEGIN
    ROLE: Bootstrap Maxitor API state with the same action pipeline as the diagram exporters.
    SIDE EFFECTS: Imports sample registration modules so the demo graph can be inspected.
    AI-CORE-END
    """
    import_sample_registration_modules()
    graph = build_registered_interchange_coordinator()
    nx_result = await machine.run(
        Context(),
        LoadGraphAction(),
        LoadGraphAction.Params(graph=graph),
    )
    sidebar_data = await machine.run(
        Context(),
        GetLeftMenuSidebarDataAction(),
        GetLeftMenuSidebarDataAction.Params(nx_graph=nx_result.nx_graph),
    )
    return MaxitorApiSession(
        sidebar_data=sidebar_data,
        nx_graph=nx_result.nx_graph,
        coordinator=graph,
        action_machine=machine,
    )
