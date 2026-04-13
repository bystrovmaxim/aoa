# tests/metadata/test_graph_execution_adapters.py
"""Tests for ``graph_execution_adapters``: facet meta rows → snapshot types."""

from __future__ import annotations

from action_machine.aspects.aspect_intent import AspectIntent
from action_machine.aspects.aspect_intent_inspector import AspectIntentInspector
from action_machine.aspects.regular_aspect_decorator import regular_aspect
from action_machine.aspects.summary_aspect_decorator import summary_aspect
from action_machine.checkers.checker_intent import CheckerIntent
from action_machine.checkers.checker_intent_inspector import CheckerIntentInspector
from action_machine.checkers.result_string_checker import result_string
from action_machine.compensate.compensate_decorator import compensate
from action_machine.compensate.compensate_intent_inspector import (
    CompensateIntentInspector,
)
from action_machine.context.context_requires_decorator import context_requires
from action_machine.context.ctx_constants import Ctx
from action_machine.metadata.base_intent_inspector import BaseIntentInspector
from action_machine.metadata.graph_execution_adapters import (
    FacetMetaRow,
    aspect_row_to_aspect,
    checker_row_to_checker,
    compensator_row_to_compensator,
    on_error_row_to_error_handler,
)
from action_machine.on_error.on_error_decorator import on_error
from action_machine.on_error.on_error_intent import OnErrorIntent
from action_machine.on_error.on_error_intent_inspector import OnErrorIntentInspector


class _RoundtripAspectAction(AspectIntent):
    @regular_aspect("A")
    async def step_aspect(self, params, state, box, connections):
        return {}

    @summary_aspect("S")
    @context_requires(Ctx.User.user_id)
    async def build_result_summary(self, params, state, box, connections, ctx):
        return {}


class _RoundtripCheckerAction(CheckerIntent):
    @result_string("f", required=False, min_length=1)
    async def only_aspect(self, params, state, box, connections):
        return {"f": "x"}


class _RoundtripCompensateAction(AspectIntent):
    @regular_aspect("X")
    async def target_aspect(self, params, state, box, connections):
        return {}

    @compensate("target_aspect", "rollback")
    @context_requires(Ctx.User.user_id)
    async def rollback_me_compensate(
        self, params, state_before, state_after, box, connections, error, ctx
    ):
        return None


class _RoundtripOnErrorAction(OnErrorIntent):
    @on_error(ValueError, description="h")
    async def value_on_error(self, params, state, box, connections, error):
        return {}


def test_aspect_row_roundtrip_matches_facet_snapshot() -> None:
    snap = AspectIntentInspector.facet_snapshot_for_class(_RoundtripAspectAction)
    assert snap is not None
    payload = AspectIntentInspector.inspect(_RoundtripAspectAction)
    assert payload is not None
    rows: tuple[FacetMetaRow, ...] = dict(payload.node_meta)["aspects"]
    assert len(rows) == len(snap.aspects)
    for row, expected in zip(rows, snap.aspects, strict=True):
        assert aspect_row_to_aspect(row) == expected


def test_checker_row_roundtrip_matches_facet_snapshot() -> None:
    snap = CheckerIntentInspector.facet_snapshot_for_class(_RoundtripCheckerAction)
    assert snap is not None
    payload = CheckerIntentInspector.inspect(_RoundtripCheckerAction)
    assert payload is not None
    rows = dict(payload.node_meta)["checkers"]
    assert len(rows) == len(snap.checkers)
    for row, expected in zip(rows, snap.checkers, strict=True):
        assert checker_row_to_checker(row) == expected


def test_compensator_row_roundtrip_matches_facet_snapshot() -> None:
    snap = CompensateIntentInspector.facet_snapshot_for_class(_RoundtripCompensateAction)
    assert snap is not None
    payload = CompensateIntentInspector.inspect(_RoundtripCompensateAction)
    assert payload is not None
    rows = dict(payload.node_meta)["compensators"]
    assert len(rows) == len(snap.compensators)
    for row, expected in zip(rows, snap.compensators, strict=True):
        assert compensator_row_to_compensator(row) == expected


def test_on_error_row_roundtrip_matches_facet_snapshot() -> None:
    snap = OnErrorIntentInspector.facet_snapshot_for_class(_RoundtripOnErrorAction)
    assert snap is not None
    payload = OnErrorIntentInspector.inspect(_RoundtripOnErrorAction)
    assert payload is not None
    rows = dict(payload.node_meta)["error_handlers"]
    assert len(rows) == len(snap.error_handlers)
    for row, expected in zip(rows, snap.error_handlers, strict=True):
        assert on_error_row_to_error_handler(row) == expected


def test_aspect_row_normalizes_context_keys_from_iterable() -> None:
    ref = object()
    row = BaseIntentInspector._make_meta(
        aspect_type="regular",
        method_name="m",
        description="d",
        method_ref=ref,
        context_keys=("a", "b"),  # not frozenset
    )
    asp = aspect_row_to_aspect(row)
    assert asp.context_keys == frozenset({"a", "b"})


def test_checker_row_accepts_extra_params_as_dict() -> None:
    row = BaseIntentInspector._make_meta(
        method_name="m",
        checker_class=int,
        field_name="f",
        required=True,
        extra_params={"x": 1},
    )
    ch = checker_row_to_checker(row)
    assert ch.extra_params == {"x": 1}
