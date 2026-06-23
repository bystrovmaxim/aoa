# packages/aoa-examples/src/aoa/examples/model/store/actions/store_ocel_traces.py
"""
Storefront OCEL trace actions — varied lifecycle paths on ``StoreDomain`` entities.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Action classes map storefront steps to distinct OCEL event types (``action.__qualname__``).
Each run appends one ``OcelEvent`` via ``OcelPlugin`` using different root entities
(order, payment capture, line pick, parcel dispatch, return) for richer object-centric views.

The OCEL store connection must be ``open()`` before the first run and ``close()``
after the last run (batch export); these actions do not manage store lifecycle.
"""

from __future__ import annotations

from typing import Any

from pydantic import Field

from aoa.action_machine.auth import GuestRole
from aoa.action_machine.context import Ctx
from aoa.action_machine.intents.aspects import regular_aspect, summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.checkers import result_instance
from aoa.action_machine.intents.connection import connection
from aoa.action_machine.intents.context_requires import context_requires
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.examples.model.store.ocel_trace_builder import (
    build_catalog_product,
    build_customer_account,
    build_entity_ocel_frame,
    build_facility_warehouse,
    build_fulfillment_task,
    build_order_line,
    build_order_ocel_frame,
    build_payment_capture,
    build_return_request,
    build_sales_order,
    build_shipment_parcel,
)
from aoa.examples.model.store.resources.ocel_store import StoreOcelStoreResource
from aoa.examples.model.store.store_domain import StoreDomain
from aoa.ocel import OCEL_FRAMES_KEY, OcelFrame
from aoa.ocel.dto import OcelAttribute

STORE_OCEL_CONNECTION_KEY = "ocel"


class StoreOcelTraceParams(BaseParams):
    """Shared params for storefront OCEL lifecycle actions."""

    order_id: str = Field(description="Sales order id")
    customer_id: str = Field(description="Customer account id")
    customer_name: str = Field(default="Store Customer", description="Buyer display name")
    customer_email: str = Field(default="buyer@store.example", description="Buyer email")
    amount: float = Field(default=99.0, ge=0, description="Order total in USD")
    storefront_channel: str = Field(default="ecommerce", description="Sales channel")
    line_id: str = Field(default="", description="Order line id")
    product_id: str = Field(default="", description="Catalog product id")
    product_sku: str = Field(default="SKU-100", description="Catalog SKU")
    product_title: str = Field(default="Trail Runner Shoe", description="Catalog title")
    capture_id: str = Field(default="", description="Payment capture id")
    task_id: str = Field(default="", description="Fulfillment task id")
    parcel_id: str = Field(default="", description="Shipment parcel id")
    facility_id: str = Field(default="wh-west-01", description="Origin warehouse id")
    return_id: str = Field(default="", description="Return request id")
    scenario: str = Field(default="standard", description="Batch scenario label")


class StoreOcelTraceResult(BaseResult):
    """Echo of exported trace metadata."""

    order_id: str = Field(description="Order id")
    customer_id: str = Field(description="Customer id")
    trace_id: str = Field(description="Request trace id used as OCEL event id")
    lifecycle_step: str = Field(description="Storefront lifecycle step label")
    scenario: str = Field(description="Scenario label from params")


def _base_event_attributes(params: StoreOcelTraceParams, lifecycle_step: str) -> list[OcelAttribute]:
    return [
        OcelAttribute(name="lifecycle_step", value=lifecycle_step),
        OcelAttribute(name="channel", value=params.storefront_channel),
        OcelAttribute(name="scenario", value=params.scenario),
    ]


def _loaded_order_graph(params: StoreOcelTraceParams, *, lifecycle_state: str):
    customer = build_customer_account(
        customer_id=params.customer_id,
        name=params.customer_name,
        email=params.customer_email,
        storefront_channel=params.storefront_channel,
    )
    order = build_sales_order(
        order_id=params.order_id,
        customer=customer,
        amount=params.amount,
        lifecycle_state=lifecycle_state,
        storefront_channel=params.storefront_channel,
    )
    product = build_catalog_product(
        product_id=params.product_id or f"prod-{params.order_id}",
        sku=params.product_sku,
        title=params.product_title,
        unit_price=max(params.amount / 2.0, 1.0),
    )
    line = build_order_line(
        line_id=params.line_id or f"line-{params.order_id}",
        order=order,
        product=product,
        quantity=2,
        unit_price=product.list_price,
        lifecycle_state="reserved",
        storefront_channel=params.storefront_channel,
    )
    return customer, order, product, line


@meta(description="Publish order-created trace for OCEL export", domain=StoreDomain)
@check_roles(GuestRole)
@connection(StoreOcelStoreResource, key=STORE_OCEL_CONNECTION_KEY, description="OCEL export store")
class PublishOrderCreatedOcelAction(
    BaseAction["PublishOrderCreatedOcelAction.Params", "PublishOrderCreatedOcelAction.Result"],
):
    Params = StoreOcelTraceParams

    class Result(StoreOcelTraceResult):
        pass

    @regular_aspect("Build OCEL frames")
    @result_instance(OCEL_FRAMES_KEY, list, required=True)
    @context_requires(Ctx.Request.trace_id)
    async def build_ocel_frames_aspect(
        self,
        params: StoreOcelTraceParams,
        state: Any,
        box: Any,
        connections: Any,
        ctx: Any,
    ) -> dict[str, Any]:
        _ = (state, box, connections, ctx)
        _, order, _, _ = _loaded_order_graph(params, lifecycle_state="confirmed")
        frame = build_order_ocel_frame(
            order,
            qualifier="Created order",
            event_attributes=[
                OcelAttribute(name="payment_status", value="pending"),
                *_base_event_attributes(params, "created"),
            ],
        )
        return {OCEL_FRAMES_KEY: [frame]}

    @summary_aspect("Finish created trace")
    @context_requires(Ctx.Request.trace_id)
    async def finish_summary(
        self,
        params: StoreOcelTraceParams,
        state: Any,
        box: Any,
        connections: Any,
        ctx: Any,
    ) -> PublishOrderCreatedOcelAction.Result:
        return PublishOrderCreatedOcelAction.Result(
            order_id=params.order_id,
            customer_id=params.customer_id,
            trace_id=str(ctx.get(Ctx.Request.trace_id)),
            lifecycle_step="created",
            scenario=params.scenario,
        )


@meta(description="Publish payment-captured trace for OCEL export", domain=StoreDomain)
@check_roles(GuestRole)
@connection(StoreOcelStoreResource, key=STORE_OCEL_CONNECTION_KEY, description="OCEL export store")
class PublishOrderPaymentOcelAction(
    BaseAction["PublishOrderPaymentOcelAction.Params", "PublishOrderPaymentOcelAction.Result"],
):
    Params = StoreOcelTraceParams

    class Result(StoreOcelTraceResult):
        pass

    @regular_aspect("Build OCEL frames")
    @result_instance(OCEL_FRAMES_KEY, list, required=True)
    @context_requires(Ctx.Request.trace_id)
    async def build_ocel_frames_aspect(
        self,
        params: StoreOcelTraceParams,
        state: Any,
        box: Any,
        connections: Any,
        ctx: Any,
    ) -> dict[str, Any]:
        _ = (state, box, connections, ctx)
        _, order, _, _ = _loaded_order_graph(params, lifecycle_state="confirmed")
        capture = build_payment_capture(
            capture_id=params.capture_id or f"pay-{params.order_id}",
            order=order,
            amount=params.amount,
            storefront_channel=params.storefront_channel,
        )
        frame = build_entity_ocel_frame(
            capture,
            qualifier="Payment captured",
            event_attributes=[
                OcelAttribute(name="payment_status", value="captured"),
                *_base_event_attributes(params, "payment"),
            ],
        )
        return {OCEL_FRAMES_KEY: [frame]}

    @summary_aspect("Finish payment trace")
    @context_requires(Ctx.Request.trace_id)
    async def finish_summary(
        self,
        params: StoreOcelTraceParams,
        state: Any,
        box: Any,
        connections: Any,
        ctx: Any,
    ) -> PublishOrderPaymentOcelAction.Result:
        return PublishOrderPaymentOcelAction.Result(
            order_id=params.order_id,
            customer_id=params.customer_id,
            trace_id=str(ctx.get(Ctx.Request.trace_id)),
            lifecycle_step="payment",
            scenario=params.scenario,
        )


@meta(description="Publish warehouse pick trace for OCEL export", domain=StoreDomain)
@check_roles(GuestRole)
@connection(StoreOcelStoreResource, key=STORE_OCEL_CONNECTION_KEY, description="OCEL export store")
class PublishOrderLinePickedOcelAction(
    BaseAction["PublishOrderLinePickedOcelAction.Params", "PublishOrderLinePickedOcelAction.Result"],
):
    Params = StoreOcelTraceParams

    class Result(StoreOcelTraceResult):
        pass

    @regular_aspect("Build OCEL frames")
    @result_instance(OCEL_FRAMES_KEY, list, required=True)
    @context_requires(Ctx.Request.trace_id)
    async def build_ocel_frames_aspect(
        self,
        params: StoreOcelTraceParams,
        state: Any,
        box: Any,
        connections: Any,
        ctx: Any,
    ) -> dict[str, Any]:
        _ = (state, box, connections, ctx)
        _, order, product, line = _loaded_order_graph(params, lifecycle_state="confirmed")
        task = build_fulfillment_task(
            task_id=params.task_id or f"task-{params.order_id}",
            order_line=line,
            assignee="picker-07",
            storefront_channel=params.storefront_channel,
        )
        frames: list[OcelFrame[Any]] = [
            build_entity_ocel_frame(
                task,
                qualifier="Picked line",
                event_attributes=_base_event_attributes(params, "pick"),
            ),
            build_entity_ocel_frame(
                line,
                qualifier="Allocated SKU",
                event_attributes=[
                    OcelAttribute(name="sku", value=product.sku),
                    OcelAttribute(name="qty", value=line.quantity),
                ],
            ),
        ]
        _ = order
        return {OCEL_FRAMES_KEY: frames}

    @summary_aspect("Finish pick trace")
    @context_requires(Ctx.Request.trace_id)
    async def finish_summary(
        self,
        params: StoreOcelTraceParams,
        state: Any,
        box: Any,
        connections: Any,
        ctx: Any,
    ) -> PublishOrderLinePickedOcelAction.Result:
        return PublishOrderLinePickedOcelAction.Result(
            order_id=params.order_id,
            customer_id=params.customer_id,
            trace_id=str(ctx.get(Ctx.Request.trace_id)),
            lifecycle_step="pick",
            scenario=params.scenario,
        )


@meta(description="Publish order-shipped trace for OCEL export", domain=StoreDomain)
@check_roles(GuestRole)
@connection(StoreOcelStoreResource, key=STORE_OCEL_CONNECTION_KEY, description="OCEL export store")
class PublishOrderShippedOcelAction(
    BaseAction["PublishOrderShippedOcelAction.Params", "PublishOrderShippedOcelAction.Result"],
):
    Params = StoreOcelTraceParams

    class Result(StoreOcelTraceResult):
        pass

    @regular_aspect("Build OCEL frames")
    @result_instance(OCEL_FRAMES_KEY, list, required=True)
    @context_requires(Ctx.Request.trace_id)
    async def build_ocel_frames_aspect(
        self,
        params: StoreOcelTraceParams,
        state: Any,
        box: Any,
        connections: Any,
        ctx: Any,
    ) -> dict[str, Any]:
        _ = (state, box, connections, ctx)
        _, order, _, _ = _loaded_order_graph(params, lifecycle_state="shipped")
        facility = build_facility_warehouse(facility_id=params.facility_id)
        parcel = build_shipment_parcel(
            parcel_id=params.parcel_id or f"parcel-{params.order_id}",
            order=order,
            facility=facility,
            storefront_channel=params.storefront_channel,
        )
        frame = build_entity_ocel_frame(
            parcel,
            qualifier="Shipped order",
            event_attributes=[
                OcelAttribute(name="carrier", value=parcel.carrier),
                *_base_event_attributes(params, "shipped"),
            ],
        )
        return {OCEL_FRAMES_KEY: [frame]}

    @summary_aspect("Finish shipped trace")
    @context_requires(Ctx.Request.trace_id)
    async def finish_summary(
        self,
        params: StoreOcelTraceParams,
        state: Any,
        box: Any,
        connections: Any,
        ctx: Any,
    ) -> PublishOrderShippedOcelAction.Result:
        return PublishOrderShippedOcelAction.Result(
            order_id=params.order_id,
            customer_id=params.customer_id,
            trace_id=str(ctx.get(Ctx.Request.trace_id)),
            lifecycle_step="shipped",
            scenario=params.scenario,
        )


@meta(description="Publish return-opened trace for OCEL export", domain=StoreDomain)
@check_roles(GuestRole)
@connection(StoreOcelStoreResource, key=STORE_OCEL_CONNECTION_KEY, description="OCEL export store")
class PublishOrderReturnOcelAction(
    BaseAction["PublishOrderReturnOcelAction.Params", "PublishOrderReturnOcelAction.Result"],
):
    Params = StoreOcelTraceParams

    class Result(StoreOcelTraceResult):
        pass

    @regular_aspect("Build OCEL frames")
    @result_instance(OCEL_FRAMES_KEY, list, required=True)
    @context_requires(Ctx.Request.trace_id)
    async def build_ocel_frames_aspect(
        self,
        params: StoreOcelTraceParams,
        state: Any,
        box: Any,
        connections: Any,
        ctx: Any,
    ) -> dict[str, Any]:
        _ = (state, box, connections, ctx)
        _, order, _, _ = _loaded_order_graph(params, lifecycle_state="shipped")
        return_request = build_return_request(
            return_id=params.return_id or f"ret-{params.order_id}",
            order=order,
            reason="size_exchange",
            storefront_channel=params.storefront_channel,
        )
        frame = build_entity_ocel_frame(
            return_request,
            qualifier="Return opened",
            event_attributes=[
                OcelAttribute(name="return_reason", value=return_request.reason),
                *_base_event_attributes(params, "return"),
            ],
        )
        return {OCEL_FRAMES_KEY: [frame]}

    @summary_aspect("Finish return trace")
    @context_requires(Ctx.Request.trace_id)
    async def finish_summary(
        self,
        params: StoreOcelTraceParams,
        state: Any,
        box: Any,
        connections: Any,
        ctx: Any,
    ) -> PublishOrderReturnOcelAction.Result:
        return PublishOrderReturnOcelAction.Result(
            order_id=params.order_id,
            customer_id=params.customer_id,
            trace_id=str(ctx.get(Ctx.Request.trace_id)),
            lifecycle_step="return",
            scenario=params.scenario,
        )


RecordOrderOcelAction = PublishOrderCreatedOcelAction
