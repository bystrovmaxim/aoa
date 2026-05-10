# packages/aoa-maxitor/src/aoa/maxitor/api/routes/diagrams.py
"""
Diagram HTML API routes.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Serve the standalone interchange graph HTML document to the React iframe viewer.

ERD is assembled entirely in the browser: the SPA loads JSON from ``GET /api/v1/erd/*``
and bundles the viewer shell from ``client/src/features/diagram-viewer/erd/shell``.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse

from aoa.maxitor.api.dependencies import get_maxitor_session
from aoa.maxitor.api.services.diagram_html import graph_html
from aoa.maxitor.api.session import MaxitorApiSession

router = APIRouter(prefix="/api/diagrams", tags=["diagrams"])


@router.get("/graph", response_class=HTMLResponse)
async def get_graph_diagram(
    session: Annotated[MaxitorApiSession, Depends(get_maxitor_session)],
) -> HTMLResponse:
    """Return the standalone interchange graph HTML document."""
    return HTMLResponse(await graph_html(session))
