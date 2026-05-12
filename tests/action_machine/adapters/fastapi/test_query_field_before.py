# tests/action_machine/adapters/fastapi/test_query_field_before.py
"""Tests for :mod:`aoa.action_machine.integrations.fastapi.query_field_before`."""

from __future__ import annotations

from typing import Annotated

import pytest
from pydantic import BaseModel

from aoa.action_machine.integrations.fastapi.query_field_before import (
    QUERY_STR_LIST_BEFORE,
    coerce_query_str_list,
)


def test_coerce_query_str_list() -> None:
    assert coerce_query_str_list(None) == []
    assert coerce_query_str_list("") == []
    assert coerce_query_str_list("  x  ") == ["x"]
    assert coerce_query_str_list([" a ", "", "b"]) == ["a", "b"]
    assert coerce_query_str_list("a,b") == ["a,b"]


def test_coerce_query_str_list_rejects_bad_type() -> None:
    with pytest.raises(TypeError):
        coerce_query_str_list(7)


def test_query_str_list_constant_with_model() -> None:
    class M(BaseModel):
        items: Annotated[list[str], QUERY_STR_LIST_BEFORE]

    assert M(items=["a", " b "]).items == ["a", "b"]
    assert M(items="solo").items == ["solo"]
