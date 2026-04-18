# src/maxitor/samples/catalog/actions/browse.py
"""Минимальное чтение каталога — отдельный домен, связанный с магазином смыслом данных."""

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


class BrowseCatalogParams(BaseParams):
    query: str = Field(default="*", description="Search token")


class BrowseCatalogResult(BaseResult):
    hits: int = Field(description="Stub hit count")


@meta(description="Browse catalog (stub)", domain=CatalogDomain)
@check_roles(NoneRole)
class BrowseCatalogAction(BaseAction[BrowseCatalogParams, BrowseCatalogResult]):
    @summary_aspect("Resolve stub hits")
    async def resolve_summary(
        self,
        params: BrowseCatalogParams,
        state: Any,
        box: Any,
        connections: Any,
    ) -> BrowseCatalogResult:
        return BrowseCatalogResult(hits=0 if params.query == "" else 1)
