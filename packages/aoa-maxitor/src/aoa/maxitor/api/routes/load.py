# packages/aoa-maxitor/src/aoa/maxitor/api/routes/load.py
"""POST /api/load — load (or reload) the coordinator graph from a remote AOA service."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from aoa.action_machine.context import Context
from aoa.action_machine.model import ParamsStub
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.maxitor.model.core.actions.left_sidebar_action import GetLeftMenuSidebarDataAction
from aoa.maxitor.model.core.actions.load_aoa_service_action import LoadAOAServiceAction, LoadAOAServiceParams
from aoa.maxitor.model.diagrams.resources.duckdb_graph_resource import DUCKDB_GRAPH_CONNECTION_KEY

router = APIRouter(prefix="/api", tags=["load"])


class LoadRequest(BaseModel):
    service_url: str


@router.post("/load")
async def load_graph(body: LoadRequest, request: Request) -> dict[str, str]:
    """Load the coordinator graph from the given AOA service URL and rebuild the sidebar."""
    machine: ActionProductMachine = request.app.state.machine
    try:
        load_result = await machine.run(
            Context(),
            LoadAOAServiceAction(),
            LoadAOAServiceParams(service_url=body.service_url),
        )
        sidebar_result = await machine.run(
            Context(),
            GetLeftMenuSidebarDataAction(),
            ParamsStub(),
            connections={DUCKDB_GRAPH_CONNECTION_KEY: load_result.graph_resource},
        )
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    request.app.state.duckdb_graph = load_result.graph_resource
    request.app.state.sidebar_data = sidebar_result
    return {"status": "ok"}
