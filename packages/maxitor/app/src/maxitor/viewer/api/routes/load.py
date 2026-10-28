# packages/maxitor/app/src/maxitor/viewer/api/routes/load.py
"""POST /api/load — rebuild one source in the graph store, leaving every other source alone."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from maxitor.viewer.api.graph_source_middleware import RETRY_AFTER_SECONDS
from maxitor.viewer.api.graph_store import GraphBuildError, GraphStoreBusyError
from pydantic import BaseModel

router = APIRouter(prefix="/api", tags=["load"])


class LoadRequest(BaseModel):
    service_url: str


@router.post("/load")
async def load_graph(body: LoadRequest, request: Request) -> dict[str, str]:
    """Rebuild the named source from its service and leave every other held graph untouched."""
    store = request.app.state.graph_store
    try:
        await store.reload(body.service_url)
    except GraphStoreBusyError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
            headers={"Retry-After": str(RETRY_AFTER_SECONDS)},
        ) from exc
    except GraphBuildError as exc:
        raise HTTPException(status_code=422, detail=exc.reason) from exc
    return {"status": "ok"}
