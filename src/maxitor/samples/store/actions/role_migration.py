# src/maxitor/samples/store/actions/role_migration.py
from __future__ import annotations

import warnings
from typing import Any

from pydantic import Field

from action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from action_machine.intents.auth.check_roles_decorator import check_roles
from action_machine.intents.meta.meta_decorator import meta
from action_machine.model.base_action import BaseAction
from action_machine.model.base_params import BaseParams
from action_machine.model.base_result import BaseResult
from maxitor.samples.roles import DeprecatedRole, EditorRole
from maxitor.samples.store.domain import StoreDomain

with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)

    @meta(description="Demo action using deprecated + editor roles", domain=StoreDomain)
    @check_roles([DeprecatedRole, EditorRole])
    class RoleMigrationAction(BaseAction["RoleMigrationAction.Params", "RoleMigrationAction.Result"]):
        class Params(BaseParams):
            item_id: str = Field(description="Legacy item id")

        class Result(BaseResult):
            migrated: bool = Field(description="Whether migration was recorded")

        @summary_aspect("Migrate")
        async def migrate_summary(
            self,
            params: RoleMigrationAction.Params,
            state: Any,
            box: Any,
            connections: Any,
        ) -> RoleMigrationAction.Result:
            return RoleMigrationAction.Result(migrated=True)
