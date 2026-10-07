"""The three answers: what each one is, what it carries, and what it refuses to be."""

from __future__ import annotations

import importlib

import pytest
from pydantic import ValidationError

from aoa.action_machine.intents.access_control import (
    FORBIDDEN_OBJECT,
    Allowed,
    Gate,
    Refused,
    Undecided,
    Verdict,
)


class TestVerdictBase:
    """The base every answer descends from, and the word it demands."""

    def test_base_cannot_be_built_without_a_word(self) -> None:
        """``Verdict()`` fails, naming the field that is missing."""
        with pytest.raises(ValidationError) as excinfo:
            Verdict()
        assert excinfo.value.errors()[0]["loc"] == ("kind",)
        assert excinfo.value.errors()[0]["type"] == "missing"

    def test_base_carries_the_word_it_was_given(self) -> None:
        """An answer has to say what it is, and the base holds exactly that."""
        assert Verdict(kind="anything").model_dump() == {"kind": "anything"}

    def test_a_word_outside_the_literal_fails(self) -> None:
        """A subclass accepts its own word and no other."""
        with pytest.raises(ValidationError) as excinfo:
            Allowed.model_validate({"kind": "refused"})
        assert excinfo.value.errors()[0]["type"] == "literal_error"


class TestAllowed:
    """The answer that lets a call continue."""

    def test_carries_nothing_but_its_word(self) -> None:
        """The whole answer is one published word."""
        assert Allowed().model_dump() == {"kind": "allowed"}


class TestRefused:
    """The answer that stops a call: the step, and the developer's reason if any."""

    def test_default_step_is_access_decide(self) -> None:
        """A bare refusal names the step a developer writes."""
        assert Refused().gate is Gate.ACCESS_DECIDE

    def test_reason_is_optional(self) -> None:
        """A refusal without a reason is valid — the framework invents no text."""
        assert Refused().reason is None

    def test_reason_is_positional(self) -> None:
        """``Refused("NOT_YOURS")`` is the short form a developer writes."""
        assert Refused("NOT_YOURS").reason == "NOT_YOURS"

    def test_step_can_be_named(self) -> None:
        """A refusal says which step refused."""
        assert Refused("X", gate=Gate.WHEN).gate is Gate.WHEN

    def test_step_outside_the_enum_fails(self) -> None:
        """A word that is not a step is rejected."""
        with pytest.raises(ValidationError) as excinfo:
            Refused.model_validate({"kind": "refused", "gate": "NOPE"})
        assert excinfo.value.errors()[0]["type"] == "enum"

    def test_empty_reason_fails(self) -> None:
        """An empty reason is not a reason."""
        with pytest.raises(ValidationError) as excinfo:
            Refused("")
        assert excinfo.value.errors()[0]["type"] == "string_too_short"

    def test_whitespace_only_reason_fails(self) -> None:
        """Neither is a reason made of spaces."""
        with pytest.raises(ValidationError) as excinfo:
            Refused("   ")
        assert excinfo.value.errors()[0]["type"] == "string_pattern_mismatch"

    def test_forbidden_object_is_one_shared_answer(self) -> None:
        """Every importer gets the same instance, and it carries no reason of its own."""
        again = importlib.import_module("aoa.action_machine.intents.access_control.refused")
        assert again.FORBIDDEN_OBJECT is FORBIDDEN_OBJECT
        assert isinstance(FORBIDDEN_OBJECT, Refused)
        assert FORBIDDEN_OBJECT.reason is None
        assert FORBIDDEN_OBJECT.gate is Gate.ACCESS_DECIDE


class TestUndecided:
    """The answer for "nobody could tell"."""

    def test_names_the_step_that_could_not_tell(self) -> None:
        """The step is the whole information the answer carries."""
        assert Undecided(Gate.GUARD).model_dump() == {"kind": "undecided", "gate": Gate.GUARD}

    def test_default_step_is_access_decide(self) -> None:
        """Without a step, the answer points at the step a developer writes."""
        assert Undecided().gate is Gate.ACCESS_DECIDE

    def test_cause_stays_out_of_every_wire_form(self) -> None:
        """The failure lives in memory and in no dump."""
        failure = RuntimeError("store is down")
        answer = Undecided(Gate.ACCESS_DECIDE, cause=failure)
        assert answer._cause is failure
        assert "cause" not in answer.model_dump()
        assert "store is down" not in answer.model_dump_json()

    def test_is_not_a_refusal(self) -> None:
        """The two answers are different words and different types."""
        assert not isinstance(Undecided(), Refused)
        assert Undecided().kind != Refused().kind

    def test_answers_are_compared_by_what_a_caller_sees(self) -> None:
        """``==`` includes the private cause, so the answer is compared through the dump."""
        one = Undecided(Gate.GUARD, cause=RuntimeError("one"))
        two = Undecided(Gate.GUARD, cause=RuntimeError("two"))
        assert one != two
        assert one.model_dump() == two.model_dump()


class TestAnswerInvariants:
    """What holds for all three answers alike."""

    @pytest.mark.parametrize("answer", [Allowed(), Refused(), Undecided()], ids=["allowed", "refused", "undecided"])
    def test_frozen(self, answer: Verdict) -> None:
        """An answer never changes after it is built."""
        with pytest.raises(ValidationError) as excinfo:
            answer.kind = "allowed"
        assert excinfo.value.errors()[0]["type"] == "frozen_instance"

    @pytest.mark.parametrize("answer", [Allowed(), Refused(), Undecided()], ids=["allowed", "refused", "undecided"])
    def test_extra_field_forbidden(self, answer: Verdict) -> None:
        """An answer never grows a field it did not declare."""
        with pytest.raises(ValidationError) as excinfo:
            type(answer).model_validate({**answer.model_dump(), "extra": 1})
        assert excinfo.value.errors()[0]["type"] == "extra_forbidden"

    def test_the_vocabulary_is_exactly_five_words(self) -> None:
        """What the framework publishes is the steps, and there are five of them."""
        assert [gate.value for gate in Gate] == [
            "AUTH_COORDINATOR",
            "CHECK_ROLES",
            "WHEN",
            "GUARD",
            "ACCESS_DECIDE",
        ]
