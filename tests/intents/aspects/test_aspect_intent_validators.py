# tests/intents/aspects/test_aspect_intent_validators.py
"""require_aspect_intent_marker and validate_aspects."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from action_machine.intents.aspects.aspect_intent import (
    AspectIntent,
    require_aspect_intent_marker,
    validate_aspects,
)


def _asp(name: str, kind: str) -> SimpleNamespace:
    return SimpleNamespace(method_name=name, aspect_type=kind)


def test_require_aspect_intent_marker_raises_without_mixin() -> None:
    class Plain:
        pass

    aspects = [_asp("x", "regular")]
    with pytest.raises(TypeError, match="AspectIntent"):
        require_aspect_intent_marker(Plain, aspects)


def test_require_aspect_intent_marker_noop_without_aspects() -> None:
    class Plain:
        pass

    require_aspect_intent_marker(Plain, [])


def test_require_aspect_intent_marker_noop_when_mixin_present() -> None:
    class With(AspectIntent):
        pass

    require_aspect_intent_marker(With, [_asp("a", "regular")])


def test_validate_aspects_noop_when_empty() -> None:
    class Host:
        __name__ = "Host"

    validate_aspects(Host, [])


def test_validate_aspects_rejects_multiple_summaries() -> None:
    class Host:
        __name__ = "Host"

    aspects = [_asp("s1", "summary"), _asp("s2", "summary")]
    with pytest.raises(ValueError, match="only one summary"):
        validate_aspects(Host, aspects)


def test_validate_aspects_requires_summary_when_regulars_exist() -> None:
    class Host:
        __name__ = "Host"

    aspects = [_asp("r", "regular")]
    with pytest.raises(ValueError, match="no summary"):
        validate_aspects(Host, aspects)


def test_validate_aspects_requires_summary_last() -> None:
    class Host:
        __name__ = "Host"

    aspects = [_asp("s", "summary"), _asp("r", "regular")]
    with pytest.raises(ValueError, match="last"):
        validate_aspects(Host, aspects)
