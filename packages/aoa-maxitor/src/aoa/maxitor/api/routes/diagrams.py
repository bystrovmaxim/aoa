# packages/aoa-maxitor/src/aoa/maxitor/api/routes/diagrams.py
"""
Diagram HTML API routes.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Serve standalone graph and ERD HTML documents to the React iframe viewer.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse

from aoa.maxitor.api.dependencies import get_maxitor_session
from aoa.maxitor.api.services.diagram_html import erd_html, graph_html
from aoa.maxitor.api.session import MaxitorApiSession

router = APIRouter(prefix="/api/diagrams", tags=["diagrams"])


@router.get("/graph", response_class=HTMLResponse)
async def get_graph_diagram(
    session: Annotated[MaxitorApiSession, Depends(get_maxitor_session)],
) -> HTMLResponse:
    """Return the standalone interchange graph HTML document."""
    return HTMLResponse(await graph_html(session))


@router.get("/erd", response_class=HTMLResponse)
async def get_erd_diagram(
    session: Annotated[MaxitorApiSession, Depends(get_maxitor_session)],
) -> HTMLResponse:
    """Return the standalone ERD HTML document for all domains."""
    return HTMLResponse(await erd_html(session))


@router.get("/erd/{domain_qualname:path}", response_class=HTMLResponse)
async def get_domain_erd_diagram(
    domain_qualname: str,
    session: Annotated[MaxitorApiSession, Depends(get_maxitor_session)],
) -> HTMLResponse:
    """Return the standalone ERD HTML document for one domain qualifier."""
    return HTMLResponse(await erd_html(session, domain_qualname=domain_qualname))
