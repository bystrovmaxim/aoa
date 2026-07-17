"""
Regression: ``build_manifest`` cannot leak access-condition bodies
(issue #130, chapter 3, implementation task 3).

The guarantee is *structural*, not a filter: the manifest is projected from
``FastApiRouteRecord`` (method, path, action class, request/response models),
which physically does not contain the body of any ``when=``, ``guard=`` or
``access_decide``. This test defends that property against a future regression
(e.g. someone enriching the manifest from the graph): each condition here
references a unique sentinel string that must never appear in the manifest.
"""

from __future__ import annotations

import json

from pydantic import Field

from aoa.action_machine.context.context import Context
from aoa.action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles, grant
from aoa.action_machine.intents.meta.meta_decorator import meta
from aoa.action_machine.model.base_action import BaseAction
from aoa.action_machine.model.base_params import BaseParams
from aoa.action_machine.model.base_result import BaseResult
from aoa.action_machine.model.base_state import BaseState
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.runtime.tools_box import ToolsBox
from aoa.fastapi.manifest import build_manifest
from aoa.fastapi.route_record import FastApiRouteRecord

from .support import ManagerRole, OrdersDomain

# Sentinels: each lives ONLY inside one condition body, nowhere in @meta or the
# param/result schemas. If any appears in the manifest, a body has leaked.
_WHEN_SENTINEL = "when-body-sentinel-8f3a91"
_GUARD_SENTINEL = "guard-body-sentinel-b7c204"
_DECIDE_SENTINEL = "decide-body-sentinel-e5d613"

_EXPECTED_KEYS = {"operation", "name", "domain", "description", "route", "params_schema", "result_schema"}


@meta(description="Fully gated action for manifest-leak regression", domain=OrdersDomain)
@check_roles(
    grant(ManagerRole, when=lambda user: str(user.user_id) != _WHEN_SENTINEL),
    guard=lambda user, params: str(params.order_id) != _GUARD_SENTINEL,
)
class _GatedAction(BaseAction["_GatedAction.Params", "_GatedAction.Result"]):
    """Carries when=, guard= and access_decide, each with its own sentinel string."""

    class Params(BaseParams):
        """Parameters — the order under consideration."""

        order_id: int = Field(description="Order identifier")

    class Result(BaseResult):
        """Result — the new order status."""

        status: str = Field(description="New order status")

    async def access_decide(
        self,
        params: _GatedAction.Params,
        context: Context,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> bool:
        secret_token = _DECIDE_SENTINEL  # lives only in this method body
        return secret_token != str(params.order_id)

    @summary_aspect("Gated summary")
    async def gated_summary(
        self,
        params: _GatedAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> _GatedAction.Result:
        return _GatedAction.Result(status="ok")


def _dump() -> str:
    record = FastApiRouteRecord(action_class=_GatedAction, method="post", path="/gated")
    return json.dumps(build_manifest([record]).model_dump(mode="json"))


class TestNoConditionBodyLeak:
    """No ``when=``/``guard=``/``access_decide`` content reaches the manifest."""

    def test_when_body_does_not_leak(self) -> None:
        assert _WHEN_SENTINEL not in _dump()

    def test_guard_body_does_not_leak(self) -> None:
        assert _GUARD_SENTINEL not in _dump()

    def test_access_decide_body_does_not_leak(self) -> None:
        assert _DECIDE_SENTINEL not in _dump()

    def test_gating_role_name_does_not_leak(self) -> None:
        # The manifest is role-independent; the gating role never appears.
        assert "ManagerRole" not in _dump()


class TestOnlySafeStructuralKeys:
    """``extra="forbid"`` makes it structurally impossible to carry condition data."""

    def test_entry_exposes_only_the_safe_keys(self) -> None:
        record = FastApiRouteRecord(action_class=_GatedAction, method="post", path="/gated")
        entry = build_manifest([record]).endpoints[0].model_dump()
        assert set(entry) == _EXPECTED_KEYS
