# packages/aoa-action-machine/tests/action_machine/exceptions/test_access_denied.py
"""
``AccessDenied`` carries the refusal and nothing else (FR-005, FR-015, SC-007).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A caller who is refused needs the decision, not a sentence about it: the gate that
refused, and the reason the developer declared beside the condition. The exception is
that decision — the same ``Refused`` the question path returns — so an adapter, a log or
a test reads the word and the reason as data.

What it must not carry is anything the framework wrote on its own: no vocabulary beside
the published words, no invented text, and no failure's text (a refusal is not a failure;
that answer is ``AccessUndecided``).

═══════════════════════════════════════════════════════════════════════════════
STRUCTURE
═══════════════════════════════════════════════════════════════════════════════

TestTheVerdictIsTheException — the verdict is reachable, whole and unchanged
TestNothingElse              — the only attribute is the verdict
TestTheMessage               — names the gate, repeats the developer's reason, invents none
"""

from __future__ import annotations

from aoa.action_machine.exceptions import AccessDenied
from aoa.action_machine.intents.access_control import Gate, Refused


class TestTheVerdictIsTheException:
    def test_a_refusal_without_a_reason_keeps_its_gate(self) -> None:
        verdict = Refused(gate=Gate.CHECK_ROLES)

        denied = AccessDenied(verdict)

        assert denied.verdict is verdict
        assert denied.verdict.gate is Gate.CHECK_ROLES
        assert denied.verdict.reason is None

    def test_a_refusal_with_a_reason_keeps_the_developers_text(self) -> None:
        verdict = Refused(gate=Gate.WHEN, reason="ONLY_SALES_AGENTS")

        denied = AccessDenied(verdict)

        assert denied.verdict.reason == "ONLY_SALES_AGENTS"

    def test_every_published_word_survives(self) -> None:
        """The gate is one of the five words, and the exception does not reword it."""
        for gate in Gate:
            assert AccessDenied(Refused(gate=gate)).verdict.gate is gate

    def test_the_verdict_is_unchanged_by_the_exception(self) -> None:
        """Passing it on does not copy, wrap or annotate it."""
        verdict = Refused(gate=Gate.GUARD, reason="SHOP_CLOSED")

        assert AccessDenied(verdict).verdict.model_dump() == verdict.model_dump()


class TestNothingElse:
    def test_the_verdict_is_the_only_attribute(self) -> None:
        """No level, no gate, no reason of its own — the vocabulary lives in the verdict."""
        denied = AccessDenied(Refused(gate=Gate.WHEN, reason="ONLY_SALES_AGENTS"))

        assert set(vars(denied)) == {"verdict"}

    def test_the_exception_is_not_an_authorization_error(self) -> None:
        """The old level vocabulary is a different exception, and this one is not it."""
        from aoa.action_machine.exceptions import AuthorizationError

        assert not issubclass(AccessDenied, AuthorizationError)


class TestTheMessage:
    def test_the_message_names_the_gate(self) -> None:
        assert str(AccessDenied(Refused(gate=Gate.WHEN))) == "Access denied by WHEN."

    def test_the_message_repeats_the_declared_reason(self) -> None:
        denied = AccessDenied(Refused(gate=Gate.WHEN, reason="ONLY_SALES_AGENTS"))

        assert str(denied) == "Access denied by WHEN: ONLY_SALES_AGENTS"

    def test_the_message_invents_nothing_where_no_reason_was_declared(self) -> None:
        """A refusal nobody explained says no more than its gate."""
        denied = AccessDenied(Refused(gate=Gate.CHECK_ROLES))

        assert str(denied) == "Access denied by CHECK_ROLES."
        assert "reason" not in str(denied).lower()
