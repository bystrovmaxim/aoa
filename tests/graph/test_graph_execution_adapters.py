# tests/graph/test_graph_execution_adapters.py
"""Facet ``FacetMetaRow`` rows round-trip to inspector snapshot types (hydrators on inspectors)."""

from __future__ import annotations

from collections import UserDict

from action_machine.graph.base_intent_inspector import BaseIntentInspector
from action_machine.graph.facet_edge import FacetMetaRow
from action_machine.legacy.aspect_intent import AspectIntent
from action_machine.legacy.aspect_intent_inspector import (
    AspectIntentInspector,
    hydrate_aspect_row,
)
from action_machine.intents.aspects.regular_aspect_decorator import regular_aspect
from action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from action_machine.legacy.checker_intent import CheckerIntent
from action_machine.legacy.checker_intent_inspector import (
    CheckerIntentInspector,
    hydrate_checker_row,
)
from action_machine.intents.checkers.result_string_decorator import result_string
from action_machine.intents.compensate.compensate_decorator import compensate
from action_machine.legacy.compensate_intent_inspector import (
    CompensateIntentInspector,
    hydrate_compensator_row,
)
from action_machine.intents.context.context_requires_decorator import context_requires
from action_machine.context.ctx_constants import Ctx
from action_machine.intents.on_error.on_error_decorator import on_error
from action_machine.legacy.on_error_intent import OnErrorIntent
from action_machine.legacy.on_error_intent_inspector import (
    OnErrorIntentInspector,
    hydrate_error_handler_row,
)
from action_machine.legacy.interchange_vertex_labels import (
    COMPENSATOR_VERTEX_TYPE,
    REGULAR_ASPECT_VERTEX_TYPE,
    SUMMARY_ASPECT_VERTEX_TYPE,
)


class _RoundtripAspectAction(AspectIntent):
    @regular_aspect("A")
    async def step_aspect(self, params, state, box, connections):
        return {}

    @summary_aspect("S")
    @context_requires(Ctx.User.user_id)
    async def build_result_summary(self, params, state, box, connections, ctx):
        return {}


class _RoundtripCheckerAction(CheckerIntent, AspectIntent):
    @regular_aspect("Roundtrip")
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
    produced = AspectIntentInspector.inspect(_RoundtripAspectAction)
    assert isinstance(produced, list)
    rows: list[FacetMetaRow] = []
    for payload in produced:
        if payload.node_type not in (
            REGULAR_ASPECT_VERTEX_TYPE,
            SUMMARY_ASPECT_VERTEX_TYPE,
        ):
            continue
        rows.extend(dict(payload.node_meta)["aspects"])
    assert len(rows) == len(snap.aspects)
    for row, expected in zip(rows, snap.aspects, strict=True):
        assert hydrate_aspect_row(row) == expected


def test_checker_row_roundtrip_matches_facet_snapshot() -> None:
    snap = CheckerIntentInspector.facet_snapshot_for_class(_RoundtripCheckerAction)
    assert snap is not None
    produced = CheckerIntentInspector.inspect(_RoundtripCheckerAction)
    assert isinstance(produced, list)
    assert len(produced) == len(snap.checkers)
    for payload, expected in zip(produced, snap.checkers, strict=True):
        row = hydrate_checker_row(payload.node_meta)
        assert row == expected


def test_compensator_row_roundtrip_matches_facet_snapshot() -> None:
    snap = CompensateIntentInspector.facet_snapshot_for_class(_RoundtripCompensateAction)
    assert snap is not None
    produced = CompensateIntentInspector.inspect(_RoundtripCompensateAction)
    assert isinstance(produced, list)
    comp_payloads = [p for p in produced if p.node_type == COMPENSATOR_VERTEX_TYPE]
    assert len(comp_payloads) == len(snap.compensators)
    for payload, expected in zip(comp_payloads, snap.compensators, strict=True):
        assert hydrate_compensator_row(payload.node_meta) == expected


def test_on_error_row_roundtrip_matches_facet_snapshot() -> None:
    snap = OnErrorIntentInspector.facet_snapshot_for_class(_RoundtripOnErrorAction)
    assert snap is not None
    produced = OnErrorIntentInspector.inspect(_RoundtripOnErrorAction)
    assert isinstance(produced, list)
    handler_payloads = [p for p in produced if p.node_type == "error_handler"]
    assert len(handler_payloads) == len(snap.error_handlers)
    for payload, expected in zip(handler_payloads, snap.error_handlers, strict=True):
        assert hydrate_error_handler_row(payload.node_meta) == expected


def test_aspect_row_normalizes_context_keys_from_iterable() -> None:
    ref = object()
    row = BaseIntentInspector._make_meta(
        aspect_type="regular",
        method_name="m",
        description="d",
        method_ref=ref,
        context_keys=("a", "b"),  # not frozenset
    )
    asp = hydrate_aspect_row(row)
    assert asp.context_keys == frozenset({"a", "b"})


def test_checker_row_accepts_extra_params_as_dict() -> None:
    row = BaseIntentInspector._make_meta(
        method_name="m",
        checker_class=int,
        field_name="f",
        required=True,
        extra_params={"x": 1},
    )
    ch = hydrate_checker_row(row)
    assert ch.extra_params == {"x": 1}


def test_checker_row_extra_params_via_non_dict_mapping() -> None:
    row = (
        ("method_name", "m"),
        ("checker_class", str),
        ("field_name", "f"),
        ("required", True),
        ("extra_params", UserDict({"k": 1})),
    )
    ch = hydrate_checker_row(row)
    assert ch.extra_params == {"k": 1}


def test_compensator_row_coerces_list_context_keys() -> None:
    row = (
        ("method_name", "comp1"),
        ("target_aspect_name", "reg"),
        ("description", "d"),
        ("method_ref", None),
        ("context_keys", ["a", "b"]),
    )
    c = hydrate_compensator_row(row)
    assert c.context_keys == frozenset({"a", "b"})


def test_on_error_row_coerces_tuple_context_keys() -> None:
    row = (
        ("method_name", "eh"),
        ("exception_types", (ValueError,)),
        ("description", "d"),
        ("method_ref", None),
        ("context_keys", ("k",)),
    )
    h = hydrate_error_handler_row(row)
    assert h.context_keys == frozenset({"k"})
