from typing import Any

import pytest

from aoa.action_machine.intents.compensate.compensate_intent_resolver import (
    CompensateIntentResolver,
)
from tests.action_machine.scenarios.domain_model.compensate_actions import CompensatedOrderAction


def _stub_compensate_fn(meta: object) -> Any:
    def fn() -> None:
        pass

    fn._compensate_meta = meta  # type: ignore[attr-defined]
    return fn


def test_resolve_compensators_returns_own_compensators() -> None:
    assert CompensateIntentResolver.resolve_compensators(CompensatedOrderAction) == [
        CompensatedOrderAction.rollback_charge_compensate,
        CompensatedOrderAction.rollback_reserve_compensate,
    ]


@pytest.mark.parametrize(
    ("meta", "expected"),
    [
        ({"description": ""}, ""),
        ({}, None),
        ({"description": "  x "}, "  x "),
    ],
)
def test_resolve_description_scratch_branches(meta: object, expected: str | None) -> None:
    stub = _stub_compensate_fn(meta)
    assert CompensateIntentResolver.resolve_description(stub) == expected


def test_resolve_description_raises_when_meta_not_dict() -> None:
    with pytest.raises(ValueError, match=r"no usable @compensate description"):
        CompensateIntentResolver.resolve_description(_stub_compensate_fn(object()))


def test_resolve_target_aspect_name_returns_stripped_compensate_target() -> None:
    assert (
        CompensateIntentResolver.resolve_target_aspect_name(
            CompensatedOrderAction.rollback_charge_compensate
        )
        == "charge_aspect"
    )
