# tests/intents/compensate/test_compensate_intent_validators.py
"""CompensateIntent validators (marker + graph consistency)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from action_machine.intents.compensate.compensate_intent import (
    CompensateIntent,
    require_compensate_intent_marker,
    validate_compensators,
)


def test_require_compensate_intent_marker_raises_without_mixin() -> None:
    class Plain:
        pass

    comps = [SimpleNamespace(method_name="c1", target_aspect_name="a")]
    with pytest.raises(TypeError, match="CompensateIntent"):
        require_compensate_intent_marker(Plain, comps)


def test_validate_compensators_noop_when_empty() -> None:
    class Host:
        __name__ = "Host"

    validate_compensators(Host, [], [])


def test_validate_compensators_unknown_target_aspect() -> None:
    class Host:
        __name__ = "Host"

    comp = SimpleNamespace(method_name="c1", target_aspect_name="missing")
    aspects = [SimpleNamespace(method_name="real", aspect_type="regular")]
    with pytest.raises(ValueError, match="missing"):
        validate_compensators(Host, [comp], aspects)


def test_validate_compensators_rejects_summary_target() -> None:
    class Host:
        __name__ = "Host"

    comp = SimpleNamespace(method_name="c1", target_aspect_name="sum")
    aspects = [SimpleNamespace(method_name="sum", aspect_type="summary")]
    with pytest.raises(ValueError, match="regular"):
        validate_compensators(Host, [comp], aspects)


def test_validate_compensators_rejects_duplicate_target() -> None:
    class Host:
        __name__ = "Host"

    aspects = [SimpleNamespace(method_name="reg", aspect_type="regular")]
    c1 = SimpleNamespace(method_name="c1", target_aspect_name="reg")
    c2 = SimpleNamespace(method_name="c2", target_aspect_name="reg")
    with pytest.raises(ValueError, match="two compensators"):
        validate_compensators(Host, [c1, c2], aspects)


def test_validate_compensators_passes_for_valid_binding() -> None:
    class Host(CompensateIntent):
        __name__ = "Host"

    aspects = [SimpleNamespace(method_name="reg", aspect_type="regular")]
    comp = SimpleNamespace(method_name="c1", target_aspect_name="reg")
    validate_compensators(Host, [comp], aspects)
