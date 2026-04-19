# tests/intents/checkers/test_checker_intent_validators.py
"""require_checker_intent_marker and validate_checkers_belong_to_aspects."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from action_machine.legacy.checker_intent import (
    CheckerIntent,
    require_checker_intent_marker,
    validate_checkers_belong_to_aspects,
)


def test_require_checker_intent_marker_raises_without_mixin() -> None:
    class Plain:
        pass

    checkers = [SimpleNamespace(field_name="f1")]
    with pytest.raises(TypeError, match="CheckerIntent"):
        require_checker_intent_marker(Plain, checkers)


def test_require_checker_intent_marker_noop_when_no_checkers() -> None:
    class Plain:
        pass

    require_checker_intent_marker(Plain, [])


def test_require_checker_intent_marker_noop_when_marker_present() -> None:
    class WithMarker(CheckerIntent):
        pass

    require_checker_intent_marker(WithMarker, [SimpleNamespace(field_name="x")])


def test_validate_checkers_belong_to_aspects_rejects_orphan_checker() -> None:
    class _Host:
        __name__ = "Host"

    checker = SimpleNamespace(
        field_name="f",
        checker_class=object,
        method_name="not_an_aspect",
    )
    aspects = [SimpleNamespace(method_name="real_aspect")]

    with pytest.raises(ValueError, match="not_an_aspect"):
        validate_checkers_belong_to_aspects(_Host, [checker], aspects)


def test_validate_checkers_belong_to_aspects_passes_when_bound_to_aspect() -> None:
    class _Host:
        __name__ = "Host"

    aspects = [
        SimpleNamespace(method_name="pay_aspect"),
        SimpleNamespace(method_name="other_aspect"),
    ]

    class _StrChk:
        pass

    checkers = [
        SimpleNamespace(
            field_name="id",
            checker_class=_StrChk,
            method_name="pay_aspect",
        ),
    ]
    validate_checkers_belong_to_aspects(_Host, checkers, aspects)
