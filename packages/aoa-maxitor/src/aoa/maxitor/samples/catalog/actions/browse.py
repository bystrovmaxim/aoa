# packages/aoa-maxitor/src/aoa/maxitor/samples/catalog/actions/browse.py
"""Minimal catalog read — separate domain, data-wise tied to the store."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from aoa.action_machine.auth import NoneRole
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.maxitor.samples.catalog.domain import CatalogDomain


@meta(description="Browse catalog (stub)", domain=CatalogDomain)
@check_roles(NoneRole)
class BrowseCatalogAction(BaseAction["BrowseCatalogAction.Params", "BrowseCatalogAction.Result"]):
    class Params(BaseParams):
        query: str = Field(default="*", description="Search token")

    class Result(BaseResult):
        hits: int = Field(description="Stub hit count")

    @summary_aspect("Resolve stub hits")
    async def resolve_summary(
        self,
        params: BrowseCatalogAction.Params,
        state: Any,
        box: Any,
        connections: Any,
    ) -> BrowseCatalogAction.Result:
        return BrowseCatalogAction.Result(hits=0 if params.query == "" else 1)
