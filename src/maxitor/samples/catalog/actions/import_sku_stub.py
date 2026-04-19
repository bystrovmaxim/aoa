# src/maxitor/samples/catalog/actions/import_sku_stub.py
from __future__ import annotations

from typing import Any

from pydantic import Field

from action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from action_machine.intents.auth.check_roles_decorator import check_roles
from action_machine.auth.none_role import NoneRole
from action_machine.intents.meta.meta_decorator import meta
from action_machine.model.base_action import BaseAction
from action_machine.model.base_params import BaseParams
from action_machine.model.base_result import BaseResult
from maxitor.samples.catalog.domain import CatalogDomain


@meta(description="Bulk SKU import placeholder (catalog sample stub)", domain=CatalogDomain)
@check_roles(NoneRole)
class ImportSkuStubAction(BaseAction["ImportSkuStubAction.Params", "ImportSkuStubAction.Result"]):
    class Params(BaseParams):
        batch_label: str = Field(description="Import batch label")

    class Result(BaseResult):
        accepted: int = Field(description="Stub accepted row count", ge=0)

    @summary_aspect("Import")
    async def import_summary(
        self,
        params: ImportSkuStubAction.Params,
        state: Any,
        box: Any,
        connections: Any,
    ) -> ImportSkuStubAction.Result:
        return ImportSkuStubAction.Result(accepted=len(params.batch_label))
