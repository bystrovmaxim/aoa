# src/maxitor/samples/catalog/actions/product_enrichment.py
"""Полная поверхность декораторов в домене catalog."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from action_machine.dependencies.depends_decorator import depends
from action_machine.intents.aspects.regular_aspect_decorator import regular_aspect
from action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from action_machine.intents.check_roles.check_roles_decorator import check_roles
from action_machine.intents.checkers.result_float_decorator import result_float
from action_machine.intents.checkers.result_string_decorator import result_string
from action_machine.intents.compensate.compensate_decorator import compensate
from action_machine.intents.context.context_requires_decorator import context_requires
from action_machine.context.ctx_constants import Ctx
from action_machine.intents.logging.sensitive_decorator import sensitive
from action_machine.intents.meta.meta_decorator import meta
from action_machine.intents.on_error.on_error_decorator import on_error
from action_machine.model.base_action import BaseAction
from action_machine.model.base_params import BaseParams
from action_machine.model.base_result import BaseResult
from action_machine.resources.connection_decorator import connection
from maxitor.samples.catalog.dependencies import IndexSyncClient, PricingFeedClient
from maxitor.samples.catalog.domain import CatalogDomain
from maxitor.samples.catalog.resources import CatalogObjectStore, CatalogSearchSidecar
from maxitor.samples.roles import EditorRole


@meta(description="Enrich catalog SKU with full graph facets (catalog demo)", domain=CatalogDomain)
@check_roles(EditorRole)
@depends(IndexSyncClient, description="Search index")
@depends(PricingFeedClient, description="Pricing feed")
@connection(CatalogSearchSidecar, key="search", description="Search sidecar")
@connection(CatalogObjectStore, key="objects", description="Object store")
class ProductEnrichmentAction(
    BaseAction["ProductEnrichmentAction.Params", "ProductEnrichmentAction.Result"],
):
    class Params(BaseParams):
        sku: str = Field(description="SKU to enrich")
        locale: str = Field(default="en", description="Locale code")

        @property
        @sensitive(True, max_chars=2, char="*", max_percent=60)
        def merchant_token_hint(self) -> str:
            return "mch-SECRET-CAT-DEMO"

    class Result(BaseResult):
        doc_id: str = Field(description="Search index document id")
        list_price: float = Field(description="Resolved list price")
        status: str = Field(description="Pipeline status")

    @regular_aspect("Validate SKU")
    @result_string("normalized_sku", required=True, min_length=1)
    @context_requires(Ctx.User.user_id)
    async def validate_sku_aspect(
        self,
        params: ProductEnrichmentAction.Params,
        state: Any,
        box: Any,
        connections: Any,
        ctx: Any,
    ) -> dict[str, Any]:
        return {"normalized_sku": params.sku.strip().upper()}

    @regular_aspect("Enrich pricing and index")
    @result_float("list_price", required=True, min_value=0.0)
    @result_string("doc_id", required=True, min_length=1)
    async def enrich_aspect(
        self,
        params: ProductEnrichmentAction.Params,
        state: Any,
        box: Any,
        connections: Any,
    ) -> dict[str, Any]:
        pricing = box.resolve(PricingFeedClient)
        price = await pricing.list_price(state.normalized_sku)
        indexer = box.resolve(IndexSyncClient)
        doc_id = await indexer.upsert_document(
            state.normalized_sku,
            {"sku": state.normalized_sku, "locale": params.locale},
        )
        return {"list_price": price, "doc_id": doc_id}

    @compensate("enrich_aspect", "Rollback index row on failure")
    async def enrich_compensate(
        self,
        params: ProductEnrichmentAction.Params,
        state_before: Any,
        state_after: Any,
        box: Any,
        connections: Any,
        error: Exception,
    ) -> None:
        if state_after is not None:
            indexer = box.resolve(IndexSyncClient)
            await indexer.upsert_document(state_after.doc_id, {"tombstone": "1"})

    @on_error(ValueError, description="SKU validation failed")
    @context_requires(Ctx.User.user_id, Ctx.Request.trace_id)
    async def validation_error_on_error(
        self,
        params: ProductEnrichmentAction.Params,
        state: Any,
        box: Any,
        connections: Any,
        error: ValueError,
        ctx: Any,
    ) -> ProductEnrichmentAction.Result:
        return ProductEnrichmentAction.Result(doc_id="ERR", list_price=0.0, status="validation_failed")

    @on_error(Exception, description="Catalog fallback")
    async def unexpected_error_on_error(
        self,
        params: ProductEnrichmentAction.Params,
        state: Any,
        box: Any,
        connections: Any,
        error: Exception,
    ) -> ProductEnrichmentAction.Result:
        return ProductEnrichmentAction.Result(doc_id="ERR", list_price=0.0, status="internal_error")

    @summary_aspect("Build enrichment result")
    async def build_result_summary(
        self,
        params: ProductEnrichmentAction.Params,
        state: Any,
        box: Any,
        connections: Any,
    ) -> ProductEnrichmentAction.Result:
        return ProductEnrichmentAction.Result(
            doc_id=state.doc_id,
            list_price=state.list_price,
            status="enriched",
        )
