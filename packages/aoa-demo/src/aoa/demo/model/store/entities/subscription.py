# packages/aoa-demo/src/aoa/demo/model/store/entities/subscription.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseCoreEntity, NoInverse
from aoa.action_machine.intents.entity import entity
from aoa.demo.model.store.entities.sales_core import CustomerAccountCoreEntity
from aoa.demo.model.store.entities.subscription_lifecycle import SubscriptionLifecycle
from aoa.demo.model.store.store_domain import StoreDomain


@entity(description="A customer's subscription to a box delivered every month", domain=StoreDomain)
class SubscriptionCoreEntity(BaseCoreEntity):
    id: str = Field(description="Subscription id")
    lifecycle: SubscriptionLifecycle = Field(description="Subscription lifecycle")
    plan_code: str = Field(description="Code of the plan the customer chose")
    renewal_day: int = Field(description="Day of the month the subscription renews", ge=1, le=28)
    customer: Annotated[
        AssociationOne[CustomerAccountCoreEntity],
        NoInverse(),
    ] = Field(description="Customer who subscribed")


SubscriptionCoreEntity.model_rebuild()
