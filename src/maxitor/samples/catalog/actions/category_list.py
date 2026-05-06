# src/maxitor/samples/catalog/actions/category_list.py
from __future__ import annotations

from typing import Any

from pydantic import Field

from action_machine.auth import NoneRole
from action_machine.intents.aspects import summary_aspect
from action_machine.intents.check_roles import check_roles
from action_machine.intents.meta import meta
from action_machine.model import BaseAction, BaseParams, BaseResult
from maxitor.samples.catalog.domain import CatalogDomain


@meta(description="List catalog categories (sample stub)", domain=CatalogDomain)
@check_roles(NoneRole)
class CategoryListAction(BaseAction["CategoryListAction.Params", "CategoryListAction.Result"]):
    class Params(BaseParams):
        root_slug: str = Field(default="all", description="Category root")

    class Result(BaseResult):
        count: int = Field(description="Stub category count", ge=0)

    @summary_aspect("List")
    async def list_summary(
        self,
        params: CategoryListAction.Params,
        state: Any,
        box: Any,
        connections: Any,
    ) -> CategoryListAction.Result:
        return CategoryListAction.Result(count=3 if params.root_slug else 0)
