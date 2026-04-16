# src/maxitor/test_domain/actions/legacy.py
"""Действие с deprecated-ролью в спецификации check_roles."""

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
from maxitor.roles import TestEditorRole, TestLegacyRole
from maxitor.test_domain.domain import TestDomain


class TestLegacyParams(BaseParams):
    item_id: str = Field(description="Legacy item id")


class TestLegacyResult(BaseResult):
    migrated: bool = Field(description="Whether migration was recorded")


with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)

    @meta(description="Synthetic legacy role action", domain=TestDomain)
    @check_roles([TestLegacyRole, TestEditorRole])
    class TestLegacyAction(BaseAction[TestLegacyParams, TestLegacyResult]):
        @summary_aspect("Migrate")
        async def migrate_summary(
            self,
            params: TestLegacyParams,
            state: Any,
            box: Any,
            connections: Any,
        ) -> TestLegacyResult:
            return TestLegacyResult(migrated=True)
