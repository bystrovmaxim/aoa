# packages/aoa-maxitor/src/aoa/maxitor/samples/catalog/actions/product_enrichment.py
"""Full decorator surface in the catalog domain."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from aoa.action_machine.context import Ctx
from aoa.action_machine.intents.aspects import regular_aspect, summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.checkers import result_float, result_string
from aoa.action_machine.intents.compensate import compensate
from aoa.action_machine.intents.connection import connection  # pylint: disable=no-name-in-module
from aoa.action_machine.intents.context_requires import context_requires
from aoa.action_machine.intents.depends import depends
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.intents.on_error import on_error
from aoa.action_machine.logging import sensitive
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.maxitor.samples.catalog.domain import CatalogDomain
from aoa.maxitor.samples.catalog.resources import CatalogObjectStore, CatalogSearchSidecar
from aoa.maxitor.samples.catalog.resources.index_sync import IndexSyncClient, IndexSyncClientResource
from aoa.maxitor.samples.catalog.resources.pricing_feed import PricingFeedClient, PricingFeedClientResource
from aoa.maxitor.samples.roles import EditorRole


@meta(description="Enrich catalog SKU with full interchange graph (catalog demo)", domain=CatalogDomain)
@check_roles(EditorRole)
@depends(
    IndexSyncClientResource,
    factory=lambda: IndexSyncClientResource(IndexSyncClient()),
    description="Search index",
)
@depends(
    PricingFeedClientResource,
    factory=lambda: PricingFeedClientResource(PricingFeedClient()),
    description="Pricing feed",
)
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
        pricing = box.resolve(PricingFeedClientResource)
        price = await pricing.service.list_price(state.normalized_sku)
        indexer = box.resolve(IndexSyncClientResource)
        doc_id = await indexer.service.upsert_document(
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
            indexer = box.resolve(IndexSyncClientResource)
            await indexer.service.upsert_document(state_after.doc_id, {"tombstone": "1"})

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
