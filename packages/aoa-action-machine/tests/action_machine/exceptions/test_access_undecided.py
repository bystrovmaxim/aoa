# packages/aoa-action-machine/tests/action_machine/exceptions/test_access_undecided.py
"""
``AccessUndecided`` is a failure to decide, not a refusal (FR-005, FR-015, SC-007).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

When a gate cannot complete — a store is down, a service answers nothing — the call is
neither allowed nor refused, and the caller must be able to tell that apart from a rule
that said no. The exception carries the ``undecided`` verdict, which names the step that
could not tell, and it is raised ``from`` the failure that stopped it, so a traceback
still shows what really happened.

Three things are pinned here: the verdict is reachable and unaltered, the failure is the
exception's cause rather than an attribute of its own, and the failure's **text** — the
part that can leak a store's name, a query or a host — appears in no message and no
answer.

═══════════════════════════════════════════════════════════════════════════════
STRUCTURE
═══════════════════════════════════════════════════════════════════════════════

TestTheVerdictIsTheException — the verdict is reachable, whole and unchanged
TestTheFailureIsTheCause    — the failure travels as the cause, not as an attribute
TestNoFailureText           — the failure's text reaches neither message nor answer
"""

from __future__ import annotations

import pytest

from aoa.action_machine.exceptions import AccessDenied, AccessUndecided
from aoa.action_machine.intents.access_control import Gate, Refused, Undecided

_FAILURE = ConnectionError("postgres://primary:5432 refused the connection")


def _verdict(gate: Gate = Gate.ACCESS_DECIDE) -> Undecided:
    """An undecided answer naming one step, carrying its failure."""
    return Undecided(gate=gate, cause=_FAILURE)


class TestTheVerdictIsTheException:
    def test_the_answer_names_the_step_that_could_not_tell(self) -> None:
        undecided = AccessUndecided(_verdict(Gate.GUARD))

        assert undecided.verdict.gate is Gate.GUARD
        assert undecided.verdict.kind == "undecided"

    def test_every_published_word_survives(self) -> None:
        for gate in Gate:
            assert AccessUndecided(_verdict(gate)).verdict.gate is gate

    def test_the_verdict_is_the_only_attribute(self) -> None:
        """No failure of its own, no level: what happened lives in the verdict's cause."""
        undecided = AccessUndecided(_verdict())

        assert set(vars(undecided)) == {"verdict"}

    def test_an_undecided_answer_is_not_a_refusal(self) -> None:
        assert not issubclass(AccessUndecided, AccessDenied)
        assert not isinstance(_verdict(), Refused)


class TestTheFailureIsTheCause:
    def test_the_failure_travels_as_the_exception_cause(self) -> None:
        with pytest.raises(AccessUndecided) as raised:
            raise AccessUndecided(_verdict()) from _FAILURE

        assert raised.value.__cause__ is _FAILURE

    def test_the_verdict_keeps_the_failure_for_a_reader_in_process(self) -> None:
        assert _verdict().cause is _FAILURE

    def test_the_traceback_names_the_step_and_the_failure(self) -> None:
        with pytest.raises(AccessUndecided) as raised:
            raise AccessUndecided(_verdict(Gate.WHEN)) from _FAILURE

        assert str(raised.value) == "Access could not be decided by WHEN."


class TestNoFailureText:
    def test_the_message_carries_no_failure_text(self) -> None:
        assert str(AccessUndecided(_verdict())) == "Access could not be decided by ACCESS_DECIDE."

    def test_the_answer_carries_no_failure_text(self) -> None:
        answer = AccessUndecided(_verdict()).verdict

        assert "postgres" not in str(answer.model_dump())
        assert "refused the connection" not in str(answer.model_dump())

    def test_the_message_of_a_refusal_carries_no_failure_text_either(self) -> None:
        assert "postgres" not in str(AccessDenied(Refused(gate=Gate.WHEN, reason="ONLY_SALES_AGENTS")))
