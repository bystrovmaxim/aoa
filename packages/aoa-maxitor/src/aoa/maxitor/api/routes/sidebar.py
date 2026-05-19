# packages/aoa-maxitor/src/aoa/maxitor/api/routes/sidebar.py
"""
Sidebar API route for the React SPA.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Serialize ``GetLeftMenuSidebarDataAction.Result`` to JSON for ``GET /api/sidebar``.
Diagram rendering stays Python-side; React only consumes this tree for navigation.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

router = APIRouter(prefix="/api", tags=["sidebar"])


def sidebar_payload(sidebar_result: Any) -> dict[str, Any]:
    """
    Turn sidebar action result rows into plain JSON-friendly dict lists.

    AI-CORE-BEGIN
    ROLE: Serialize Maxitor sidebar action rows into the stable React API shape.
    INPUT/OUTPUT: Accepts action result objects and emits primitive JSON data.
    AI-CORE-END
    """

    def row(n: Any) -> dict[str, Any]:
        out: dict[str, Any] = {
            "id": str(n.id),
            "parent_id": None if n.parent_id is None else str(n.parent_id),
            "label": str(n.label),
            "type": str(n.type),
        }
        ord_ = getattr(n, "ordinal", None)
        if ord_ is not None:
            out["ordinal"] = int(ord_)
        return out

    return {
        "level1_nodes": [row(n) for n in sidebar_result.level1_nodes],
        "level2_diagrams": [row(n) for n in sidebar_result.level2_diagrams],
        "level2_nodes": [row(n) for n in sidebar_result.level2_nodes],
        "level3_diagrams": [row(n) for n in sidebar_result.level3_diagrams],
    }


@router.get("/sidebar")
async def get_sidebar(request: Request) -> dict[str, Any]:
    """Return sidebar navigation data for the React SPA."""
    return sidebar_payload(request.app.state.sidebar_data)
