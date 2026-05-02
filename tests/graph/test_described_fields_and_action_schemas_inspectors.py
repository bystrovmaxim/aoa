# tests/graph/test_described_fields_and_action_schemas_inspectors.py
"""Tests for :mod:`action_machine.model.described_schema_validation` (params/result/action wiring)."""

from __future__ import annotations

import pytest
from pydantic import Field

from action_machine.auth.none_role import NoneRole
from action_machine.domain.base_domain import BaseDomain
from action_machine.intents.check_roles import check_roles
from action_machine.intents.meta.meta_decorator import meta
from action_machine.model.base_action import BaseAction
from action_machine.model.base_params import BaseParams
from action_machine.model.base_result import BaseResult
from action_machine.model.described_schema_validation import (
    validate_described_schema,
    validate_described_schemas_for_action,
)


class _ProbeParams(BaseParams):
    probe_id: str = Field(description="Probe identifier")


class _ProbeResult(BaseResult):
    ok: bool = Field(default=True, description="Probe outcome flag")


class _ProbeDomain(BaseDomain):
    name = "probe"
    description = "Probe domain"


@meta(description="Schema link probe", domain=_ProbeDomain)
@check_roles(NoneRole)
class _SchemaLinkProbeAction(BaseAction[_ProbeParams, _ProbeResult]):
    """Minimal action with concrete params/result types."""

    pass


def test_validate_described_schema_no_op_for_none_and_empty_shell() -> None:
    validate_described_schema(None)
    validate_described_schema(BaseParams)  # no declared fields


def test_validate_described_schema_raises_on_missing_description() -> None:
    class _BadParams(BaseParams):
        x: str

    with pytest.raises(TypeError, match="do not have descriptions"):
        validate_described_schema(_BadParams)


def test_validate_described_schemas_for_action_validates_linked_types() -> None:
    validate_described_schemas_for_action(_SchemaLinkProbeAction)
