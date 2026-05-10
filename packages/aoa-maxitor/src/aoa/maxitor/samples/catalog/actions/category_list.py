# packages/aoa-maxitor/src/aoa/maxitor/samples/catalog/actions/category_list.py
from __future__ import annotations

from typing import Any

from pydantic import Field

from aoa.action_machine.auth import NoneRole
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult, JsonSchemaValue
from aoa.maxitor.samples.catalog.domain import CatalogDomain

_SAMPLE_AUDIT_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "events": {
            "type": "array",
            "items": {"type": "object", "properties": {}, "additionalProperties": False},
        },
        "source": {"type": "string"},
    },
    "required": ["events", "source"],
    "additionalProperties": False,
}
_CatalogCategoryListSampleAuditJson = JsonSchemaValue.define(
    name="CatalogCategoryListSampleAuditJson",
    schema=_SAMPLE_AUDIT_SCHEMA,
)


@meta(description="List catalog categories (sample stub)", domain=CatalogDomain)
@check_roles(NoneRole)
class CategoryListAction(BaseAction["CategoryListAction.Params", "CategoryListAction.Result"]):
    class Params(BaseParams):
        root_slug: str = Field(default="all", description="Category root")

    class Result(BaseResult):
        count: int = Field(description="Stub category count", ge=0)
        sample_audit: _CatalogCategoryListSampleAuditJson = Field(
            description="Sample JSON payload for JsonSchemaValue graph metadata",
        )

    @summary_aspect("List")
    async def list_summary(
        self,
        params: CategoryListAction.Params,
        state: Any,
        box: Any,
        connections: Any,
    ) -> CategoryListAction.Result:
        return CategoryListAction.Result(
            count=3 if params.root_slug else 0,
            sample_audit={"events": [], "source": "catalog_category_list"},
        )
