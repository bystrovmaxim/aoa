# src/maxitor/samples/catalog/actions/category_list.py
from __future__ import annotations

from typing import Any

from pydantic import Field

from action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from action_machine.intents.auth.check_roles_decorator import check_roles
from action_machine.intents.auth.none_role import NoneRole
from action_machine.intents.meta.meta_decorator import meta
from action_machine.model.base_action import BaseAction
from action_machine.model.base_params import BaseParams
from action_machine.model.base_result import BaseResult
from maxitor.samples.catalog.domain import CatalogDomain


class CategoryListParams(BaseParams):
    root_slug: str = Field(default="all", description="Category root")


class CategoryListResult(BaseResult):
    count: int = Field(description="Stub category count", ge=0)


@meta(description="List catalog categories (sample stub)", domain=CatalogDomain)
@check_roles(NoneRole)
class CategoryListAction(BaseAction[CategoryListParams, CategoryListResult]):
    @summary_aspect("List")
    async def list_summary(
        self,
        params: CategoryListParams,
        state: Any,
        box: Any,
        connections: Any,
    ) -> CategoryListResult:
        return CategoryListResult(count=3 if params.root_slug else 0)
