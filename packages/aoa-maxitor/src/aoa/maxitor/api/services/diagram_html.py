# packages/aoa-maxitor/src/aoa/maxitor/api/services/diagram_html.py
"""
Diagram HTML service for FastAPI routes.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Keep route handlers small by centralising graph / ERD orchestration while
reusing the pure HTML renderers under :mod:`aoa.maxitor.diagrams`.
"""

from __future__ import annotations

import asyncio
from typing import Any

from aoa.action_machine.context.context import Context
from aoa.maxitor.api.session import MaxitorApiSession
from aoa.maxitor.diagrams.erd.html_page import erd_html_string
from aoa.maxitor.diagrams.graph.coordinator_violations import dag_cycle_violation_keys_from_coordinator
from aoa.maxitor.diagrams.graph.html_page import interchange_g6_html_string_from_nx
from aoa.maxitor.model.app_view.actions.build_erd_graph_data_action import BuildErdGraphDataAction


async def graph_html(session: MaxitorApiSession) -> str:
    """
    Return the standalone interchange graph page.

    AI-CORE-BEGIN
    ROLE: Render the current NetworkX graph to the existing G6 standalone HTML page.
    SIDE EFFECTS: Runs CPU-heavy serialization in a worker thread so request handling remains responsive.
    AI-CORE-END
    """
    keys = dag_cycle_violation_keys_from_coordinator(session.coordinator)
    return await asyncio.to_thread(
        interchange_g6_html_string_from_nx,
        session.nx_graph,
        title="Interchange graph",
        cycle_violation_keys=keys,
    )


async def erd_html(
    session: MaxitorApiSession,
    *,
    domain_qualname: str | None = None,
    title: str | None = None,
) -> str:
    """
    Return the standalone ERD page for all domains or one domain qualifier.

    AI-CORE-BEGIN
    ROLE: Run ``BuildErdGraphDataAction`` and render its result through the ERD HTML renderer.
    CONTRACT: ``domain_qualname`` is a fully-qualified ``BaseDomain`` type id or ``None`` for all domains.
    AI-CORE-END
    """
    erd_result = await session.action_machine.run(
        Context(),
        BuildErdGraphDataAction(),
        BuildErdGraphDataAction.Params(
            nx_graph=session.nx_graph,
            domain_qualname=domain_qualname,
        ),
    )
    erd_data: dict[str, Any] = {
        "domains": erd_result.domains_map,
        "domain_qualifiers": erd_result.domain_qualifiers,
    }
    page_title = title or ("Interchange ERD" if domain_qualname is None else f"ERD - {domain_qualname.rsplit('.', 1)[-1]}")
    return await asyncio.to_thread(erd_html_string, erd_data, title=page_title)
