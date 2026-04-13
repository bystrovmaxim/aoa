# tests/intents/meta/test_validate_meta_required.py
"""validate_meta_required enforcement for actions and resource managers."""

from __future__ import annotations

import pytest

from action_machine.intents.aspects.regular_aspect_decorator import regular_aspect
from action_machine.intents.auth import NoneRole, check_roles
from action_machine.intents.meta.meta_intents import validate_meta_required
from action_machine.model.base_action import BaseAction
from action_machine.model.base_params import BaseParams
from action_machine.model.base_result import BaseResult
from action_machine.resources.base_resource_manager import BaseResourceManager


def test_validate_meta_required_noop_when_meta_present() -> None:
    @check_roles(NoneRole)
    class _OkMetaAction(BaseAction[BaseParams, BaseResult]):
        _meta_info = {"description": "x", "domain": None}

        @regular_aspect("r")
        async def r_aspect(self, params, state, box, connections):
            return {}

    validate_meta_required(_OkMetaAction, True, [object()])


def test_validate_meta_required_action_with_aspects_without_meta_raises() -> None:
    @check_roles(NoneRole)
    class _BadMetaAction(BaseAction[BaseParams, BaseResult]):
        @regular_aspect("r")
        async def r_aspect(self, params, state, box, connections):
            return {}

    with pytest.raises(TypeError, match="missing @meta"):
        validate_meta_required(_BadMetaAction, False, [object()])


def test_validate_meta_required_resource_manager_without_meta_raises() -> None:
    class _BadRm(BaseResourceManager):
        def get_wrapper_class(self):
            return None

    with pytest.raises(TypeError, match="Resource manager"):
        validate_meta_required(_BadRm, False, [])
