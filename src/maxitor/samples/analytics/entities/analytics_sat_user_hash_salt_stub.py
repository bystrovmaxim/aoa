# src/maxitor/samples/analytics/entities/analytics_sat_user_hash_salt_stub.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.analytics.domain import AnalyticsDomain
from maxitor.samples.analytics.entities.an_dense_lifecycle import AnalyticsPipelineLifecycle
from maxitor.samples.analytics.entities.analytics_sat_time_bucket_mapper import TimeBucketMapperEntity


@entity(description="Hash salt bookkeeping continuing time-bucket spine", domain=AnalyticsDomain)
class UserHashSaltStubEntity(BaseEntity):
    id: str = Field(description="Salt id")
    lifecycle: AnalyticsPipelineLifecycle = Field(description="Salt stub lifecycle")

    bucket_mapper: Annotated[
        AssociationOne[TimeBucketMapperEntity],
        NoInverse(),
    ] = Rel(description="Upstream bucket mapper facet")  # type: ignore[assignment]


UserHashSaltStubEntity.model_rebuild()
