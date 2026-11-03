# packages/aoa-demo/src/aoa/demo/model/catalog/actions/review_submit.py
from __future__ import annotations

from pydantic import Field

from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult, BaseState
from aoa.action_machine.resources import Connections
from aoa.action_machine.runtime.tools_box import ToolsBox
from aoa.demo.model.catalog.domain import CatalogDomain
from aoa.demo.model.catalog.review_moderator_role import ReviewModeratorRole


@meta(description="Publish a customer's review of a product (sample stub)", domain=CatalogDomain)
@check_roles(ReviewModeratorRole)
class ReviewSubmitAction(BaseAction["ReviewSubmitAction.Params", "ReviewSubmitAction.Result"]):
    class Params(BaseParams):
        product_id: str = Field(description="Product the review is about")
        rating: int = Field(description="Stars, from 1 to 5", ge=1, le=5)
        text: str = Field(description="What the customer wrote")

    class Result(BaseResult):
        review_id: str = Field(description="Id of the published review")

    @summary_aspect("Publish review")
    async def publish_summary(
        self,
        params: ReviewSubmitAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
    ) -> ReviewSubmitAction.Result:
        return ReviewSubmitAction.Result(review_id=f"{params.product_id}:{params.rating}")
