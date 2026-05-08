# src/maxitor/samples/store/actions/role_migration.py
from __future__ import annotations

import warnings
from typing import Any

from pydantic import Field

from action_machine.intents.aspects import summary_aspect
from action_machine.intents.check_roles import check_roles
from action_machine.intents.meta import meta
from action_machine.model import BaseAction, BaseParams, BaseResult
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
