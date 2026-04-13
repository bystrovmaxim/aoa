# tests/domain/test_core_schema_extra.py
"""
Extra tests for `BaseSchema` helpers used by the domain stack.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

`BaseEntity` builds on schema machinery; this module exercises **dict-like**
access (`__getitem__` / `__setitem__` rules) and **dot-path** `resolve()` for
nested structures. Keeps coverage for edge paths not duplicated in entity
tests.

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS / BEHAVIOR
═══════════════════════════════════════════════════════════════════════════════

- `resolve()` is **fail-soft**: unknown or unsupported paths return `None` (or
  default), not exceptions — see individual tests for exact cases.

═══════════════════════════════════════════════════════════════════════════════
ERRORS
═══════════════════════════════════════════════════════════════════════════════

- **KeyError** — invalid key for `__getitem__`.
- **TypeError** — invalid key assignment via `__setitem__`.
"""

from __future__ import annotations

import pytest

from action_machine.model.base_schema import BaseSchema


class _Child(BaseSchema):
    name: str


class _Root(BaseSchema):
    value: int
    child: _Child
    entries: list[_Child]


def test_base_schema_getitem_setitem_to_dict_and_key_errors() -> None:
    obj = _Root(value=1, child=_Child(name="x"), entries=[_Child(name="a")])
    assert obj["value"] == 1
    assert obj.model_dump()["value"] == 1
    with pytest.raises(KeyError):
        _ = obj["missing"]
    with pytest.raises(TypeError):
        obj["value"] = 2


def test_base_schema_resolve_happy_paths() -> None:
    obj = _Root(value=1, child=_Child(name="x"), entries=[_Child(name="a"), _Child(name="b")])
    assert obj.resolve("value") == 1
    assert obj.resolve("child.name") == "x"
    # Current BaseSchema.resolve returns default/None when path can't be resolved.
    assert obj.resolve("entries.0.name") is None
    assert obj.resolve("entries.*.name") is None


def test_base_schema_resolve_error_paths() -> None:
    obj = _Root(value=1, child=_Child(name="x"), entries=[_Child(name="a")])
    # BaseSchema.resolve is fail-soft: unresolved paths return None/default.
    assert obj.resolve("") is None
    assert obj.resolve("entries.*") is None
    assert obj.resolve("entries.z.name") is None
    assert obj.resolve("unknown.field") is None
