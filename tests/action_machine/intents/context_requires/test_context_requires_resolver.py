# tests/intents/context_requires/test_context_requires_resolver.py
"""Tests for :class:`~aoa.action_machine.intents.context_requires.context_requires_resolver.ContextRequiresResolver`."""

from __future__ import annotations

import pytest

from aoa.action_machine.context.ctx_constants import Ctx
from aoa.action_machine.intents.context_requires.context_requires_decorator import (
    context_requires,
)
from aoa.action_machine.intents.context_requires.context_requires_resolver import (
    ContextRequiresResolver,
)


@pytest.mark.parametrize(
    ("keys_decorator_args", "expected_sorted"),
    [
        (
            (Ctx.User.user_id,),
            ["user.user_id"],
        ),
        (
            (Ctx.Request.trace_id, Ctx.User.user_id),
            ["request.trace_id", "user.user_id"],
        ),
        (
            ("zz.top", "aa.first"),
            ["aa.first", "zz.top"],
        ),
    ],
)
def test_resolver_matches_decorator_frozenset(
    keys_decorator_args: tuple[str, ...],
    expected_sorted: list[str],
) -> None:
    @context_requires(*keys_decorator_args)
    async def aspect(self, *_a: object) -> None:
        pass

    assert (
        ContextRequiresResolver.resolve_required_context_keys(aspect) == expected_sorted
    )


def test_resolver_accepts_bound_method() -> None:
    class Host:
        @context_requires(Ctx.Runtime.hostname)
        async def boom(self, *_a: object) -> None:
            pass

    inst = Host()
    assert ContextRequiresResolver.resolve_required_context_keys(
        inst.boom,
    ) == ["runtime.hostname"]


def test_plain_callable_returns_empty() -> None:
    async def no_ctx(self, *_a: object) -> None:
        pass

    assert ContextRequiresResolver.resolve_required_context_keys(no_ctx) == []


def test_non_decorated_lambda_returns_empty() -> None:
    assert ContextRequiresResolver.resolve_required_context_keys(lambda: None) == []
