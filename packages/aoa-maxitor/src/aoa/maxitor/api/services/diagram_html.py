# packages/aoa-maxitor/src/aoa/maxitor/api/services/diagram_html.py
"""
Diagram HTML service for FastAPI routes.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Keep route handlers small by centralising graph orchestration while reusing the
pure HTML renderer under :mod:`aoa.maxitor.diagrams.graph`.
"""

from __future__ import annotations

import asyncio

from aoa.maxitor.api.session import MaxitorApiSession
from aoa.maxitor.diagrams.graph.coordinator_violations import dag_cycle_violation_keys_from_coordinator
from aoa.maxitor.diagrams.graph.html_page import interchange_g6_html_string_from_nx


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
