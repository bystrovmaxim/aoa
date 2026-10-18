# packages/aoa-action-machine/tests/action_machine/intents/aspects/test_aspect_signature_names.py
"""
Tests for the declaration-time shape of an aspect signature — the names in order.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The pipeline hands an aspect four values, in one order, and Python binds them by
position. A declaration that renames or reorders them still runs, and receives something
other than it says. These tests pin the refusal of that shape, for all four decorators,
at the moment the method is declared: the names and their order, the trailing ``ctx``
that only a visible ``@context_requires`` may add, and a signature the machine can
actually call positionally.

The fragments asserted here are the ones `contracts/refusals.md` quotes as the contract:
R-1 (names and order), R-2 (the ``ctx`` mismatch, in both directions) and R-3 (the
signature cannot be called by position, or carries a default).

═══════════════════════════════════════════════════════════════════════════════
STRUCTURE
═══════════════════════════════════════════════════════════════════════════════

TestTheNamesInOrder        — a renamed or reordered declaration is refused, per decorator
TestTheContextParameter    — the trailing ``ctx`` follows ``@context_requires``, not the author
TestASignatureThatIsCalled — keyword-only, ``*args``, ``**kwargs`` and defaults
TestThatStillPasses        — a correct declaration is accepted, with and without context
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from aoa.action_machine.context.context_view import ContextView
from aoa.action_machine.exceptions import AspectSignatureError
from aoa.action_machine.intents.aspects import regular_aspect, summary_aspect
from aoa.action_machine.intents.compensate import compensate
from aoa.action_machine.intents.context_requires import context_requires
from aoa.action_machine.intents.on_error import on_error

SUMMARY_ORDER = "self, params, state, box, connections"
ON_ERROR_ORDER = "self, params, state, box, connections, error"
COMPENSATE_ORDER = "self, params, state_before, state_after, box, connections, error"


async def charge_aspect(self: Any, params: Any, state: Any, box: Any, connections: Any) -> dict[str, Any]:
    """A target regular aspect, for the compensator's required reference."""
    return {}


def _refused(apply: Callable[[Callable[..., Any]], Any], func: Callable[..., Any]) -> AspectSignatureError:
    """Apply the decorator and return the refusal it must raise."""
    with pytest.raises(AspectSignatureError) as caught:
        apply(func)
    return caught.value


class TestTheNamesInOrder:
    """A renamed or reordered declaration is refused, for every one of the four."""

    def test_a_renamed_summary_is_refused(self) -> None:
        async def renamed_summary(self: Any, p: Any, state: Any, box: Any, connections: Any) -> Any:
            return None

        error = _refused(summary_aspect("S"), renamed_summary)
        assert "must declare its parameters as" in str(error)
        assert f"({SUMMARY_ORDER})" in str(error)
        assert "(self, p, state, box, connections)" in str(error)
        assert "binds by position" in str(error)

    def test_a_reordered_summary_is_refused(self) -> None:
        async def shuffled_summary(self: Any, state: Any, params: Any, box: Any, connections: Any) -> Any:
            return None

        error = _refused(summary_aspect("S"), shuffled_summary)
        assert "must declare its parameters as" in str(error)
        assert "(self, state, params, box, connections)" in str(error)

    def test_a_renamed_regular_aspect_is_refused(self) -> None:
        async def renamed_aspect(self: Any, s: Any, b: Any, c: Any, p: Any) -> Any:
            return {}

        error = _refused(regular_aspect("R"), renamed_aspect)
        assert "must declare its parameters as" in str(error)
        assert f"({SUMMARY_ORDER})" in str(error)

    def test_an_on_error_handler_with_the_error_in_the_wrong_place_is_refused(self) -> None:
        async def misplaced_on_error(
            self: Any,
            params: Any,
            error: Any,
            state: Any,
            box: Any,
            connections: Any,
        ) -> Any:
            return None

        error = _refused(on_error(ValueError, description="E"), misplaced_on_error)
        assert f"({ON_ERROR_ORDER})" in str(error)

    def test_a_compensator_with_its_states_swapped_is_refused(self) -> None:
        async def swapped_compensate(
            self: Any,
            params: Any,
            state_after: Any,
            state_before: Any,
            box: Any,
            connections: Any,
            error: Any,
        ) -> None:
            return None

        error = _refused(compensate(charge_aspect, "C"), swapped_compensate)
        assert f"({COMPENSATE_ORDER})" in str(error)

    def test_the_refusal_names_the_declaration_it_refuses(self) -> None:
        async def another_summary(self: Any, params: Any, st: Any, box: Any, connections: Any) -> Any:
            return None

        error = _refused(summary_aspect("S"), another_summary)
        assert "another_summary" in str(error)


class TestTheContextParameter:
    """The trailing ``ctx`` follows ``@context_requires``, not the author's memory."""

    def test_taking_ctx_without_asking_for_context_is_refused(self) -> None:
        async def unasked_summary(
            self: Any,
            params: Any,
            state: Any,
            box: Any,
            connections: Any,
            ctx: ContextView,
        ) -> Any:
            return None

        error = _refused(summary_aspect("S"), unasked_summary)
        assert "put @context_requires(...) under the @summary_aspect decorator" in str(error)

    def test_asking_for_context_without_taking_ctx_is_refused(self) -> None:
        @context_requires("user.id")
        async def undeclared_summary(self: Any, params: Any, state: Any, box: Any, connections: Any) -> Any:
            return None

        error = _refused(summary_aspect("S"), undeclared_summary)
        assert "must take the trailing ctx parameter" in str(error)

    def test_the_same_two_directions_are_refused_for_a_regular_aspect(self) -> None:
        async def unasked_aspect(
            self: Any,
            params: Any,
            state: Any,
            box: Any,
            connections: Any,
            ctx: ContextView,
        ) -> Any:
            return {}

        error = _refused(regular_aspect("R"), unasked_aspect)
        assert "put @context_requires(...) under the @regular_aspect decorator" in str(error)


class TestASignatureThatIsCalled:
    """The machine calls by position, so a signature it cannot call that way is refused."""

    def test_keyword_only_parameters_are_refused(self) -> None:
        async def keyword_summary(self: Any, params: Any, state: Any, box: Any, *, connections: Any) -> Any:
            return None

        error = _refused(summary_aspect("S"), keyword_summary)
        assert "must be callable with positional arguments" in str(error)

    def test_star_args_is_refused(self) -> None:
        async def variadic_summary(self: Any, params: Any, state: Any, box: Any, *connections: Any) -> Any:
            return None

        error = _refused(summary_aspect("S"), variadic_summary)
        assert "must be callable with positional arguments" in str(error)

    def test_star_kwargs_is_refused(self) -> None:
        async def kwargs_summary(self: Any, params: Any, state: Any, box: Any, **connections: Any) -> Any:
            return None

        error = _refused(summary_aspect("S"), kwargs_summary)
        assert "must be callable with positional arguments" in str(error)

    def test_a_default_on_a_parameter_the_pipeline_supplies_is_refused(self) -> None:
        async def defaulted_summary(
            self: Any,
            params: Any,
            state: Any = None,
            box: Any = None,
            connections: Any = None,
        ) -> Any:
            return None

        error = _refused(summary_aspect("S"), defaulted_summary)
        assert "without a default" in str(error)


class TestThatStillPasses:
    """A correct declaration is accepted — the rule refuses mistakes, not writing."""

    def test_the_plain_order_is_accepted(self) -> None:
        async def good_summary(self: Any, params: Any, state: Any, box: Any, connections: Any) -> Any:
            return None

        assert summary_aspect("S")(good_summary) is good_summary

    def test_the_order_with_context_under_the_declaration_is_accepted(self) -> None:
        @context_requires("user.id")
        async def contextual_summary(
            self: Any,
            params: Any,
            state: Any,
            box: Any,
            connections: Any,
            ctx: ContextView,
        ) -> Any:
            return None

        assert summary_aspect("S")(contextual_summary) is contextual_summary

    def test_a_compensator_in_its_own_order_is_accepted(self) -> None:
        async def good_compensate(
            self: Any,
            params: Any,
            state_before: Any,
            state_after: Any,
            box: Any,
            connections: Any,
            error: Any,
        ) -> None:
            return None

        assert compensate(charge_aspect, "C")(good_compensate) is good_compensate
