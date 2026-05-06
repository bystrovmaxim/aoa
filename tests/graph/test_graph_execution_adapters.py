# tests/graph/test_graph_execution_adapters.py
"""Hydration tests for decorator-scratch tuples that feed module-level helpers."""

from __future__ import annotations

from collections import UserDict
from typing import Any, cast

from action_machine.intents.on_error.on_error_decorator import on_error
from action_machine.intents.on_error.on_error_intent import OnErrorIntent
from action_machine.intents.on_error.on_error_intent_resolver import hydrate_error_handler_row
from action_machine.system_core import TypeIntrospection
from action_machine.testing.checker_interchange_snapshot import CheckerInterchangeSnapshot


def _checker_from_meta(row: tuple[tuple[str, Any], ...]) -> CheckerInterchangeSnapshot.Checker:
    """Test-local rebuild of checker row meta (parity with coordinator interchange rows)."""
    d = dict(row)
    extra = d["extra_params"]
    ep = extra if isinstance(extra, dict) else dict(extra)
    return CheckerInterchangeSnapshot.Checker(
        method_name=d["method_name"],
        checker_class=d["checker_class"],
        field_name=d["field_name"],
        required=bool(d["required"]),
        extra_params=ep,
    )


class _RoundtripOnErrorAction(OnErrorIntent):
    @on_error(ValueError, description="h")
    async def value_on_error(self, params, state, box, connections, error):
        return {}


def test_on_error_interchange_row_hydrates_from_decorator_scratch() -> None:
    meth = _RoundtripOnErrorAction.value_on_error
    func = TypeIntrospection.unwrap_declaring_class_member(meth)
    meta = getattr(func, "_on_error_meta", {})
    assert isinstance(meta, dict)
    raw_et = meta.get("exception_types")
    if isinstance(raw_et, type):
        exc_tuple = cast("tuple[type[Exception], ...]", (raw_et,))
    else:
        exc_tuple = cast("tuple[type[Exception], ...]", tuple(raw_et))
    ctx = getattr(func, "_required_context_keys", ()) or ()
    row = tuple(
        {
            "method_name": "value_on_error",
            "exception_types": exc_tuple,
            "description": str(meta.get("description", "") or ""),
            "method_ref": func,
            "context_keys": ctx,
        }.items(),
    )
    hydrated = hydrate_error_handler_row(row)
    assert hydrated.method_name == "value_on_error"
    assert hydrated.exception_types == exc_tuple
    assert hydrated.description == "h"
    assert hydrated.method_ref is func


def test_checker_row_accepts_extra_params_as_dict() -> None:
    row = tuple(
        {
            "method_name": "m",
            "checker_class": int,
            "field_name": "f",
            "required": True,
            "extra_params": {"x": 1},
        }.items(),
    )
    ch = _checker_from_meta(row)
    assert ch.extra_params == {"x": 1}


def test_checker_row_extra_params_via_non_dict_mapping() -> None:
    row = (
        ("method_name", "m"),
        ("checker_class", str),
        ("field_name", "f"),
        ("required", True),
        ("extra_params", UserDict({"k": 1})),
    )
    ch = _checker_from_meta(row)
    assert ch.extra_params == {"k": 1}


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
