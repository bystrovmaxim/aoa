# src/maxitor/samples/billing/entities/billing_sat_interchange_slice.py
"""Standalone interchange economics root row."""

from __future__ import annotations

from pydantic import Field

from action_machine.domain import BaseEntity
from action_machine.intents.entity import entity
from maxitor.samples.billing.domain import BillingDomain
from maxitor.samples.billing.entities.billing_dense_lifecycle import BillingDenseLifecycle


@entity(description="Interchange economics slice", domain=BillingDomain)
class InterchangeAssessmentSliceEntity(BaseEntity):
    lifecycle: BillingDenseLifecycle = Field(description="Interchange slice lifecycle")
    id: str = Field(description="Slice id")


InterchangeAssessmentSliceEntity.model_rebuild()
