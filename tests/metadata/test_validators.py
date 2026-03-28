# tests/metadata/test_validators.py
"""
Тесты валидаторов gate-host — функции validate_gate_hosts().
"""

import pytest

from action_machine.aspects import AspectGateHost
from action_machine.checkers.checker_gate_host import CheckerGateHost
from action_machine.core.class_metadata import AspectMeta, CheckerMeta
from action_machine.metadata.validators import validate_gate_hosts
from action_machine.plugins.on_gate_host import OnGateHost


def _make_aspect(name: str, kind: str = "regular") -> AspectMeta:
    return AspectMeta(method_name=name, aspect_type=kind, description=f"Aspect {name}", method_ref=None)

def _make_checker(method_name: str, field: str) -> CheckerMeta:
    return CheckerMeta(
        method_name=method_name, checker_class=type("FakeChecker", (), {}),
        field_name=field, description=f"Check {field}", required=True, extra_params={},
    )

class FakeSubscription:
    def __init__(self, event_type: str):
        self.event_type = event_type


class TestAspectGateHostValidation:
    def test_aspects_without_host_raises(self):
        cls = type("Bad", (), {})
        with pytest.raises(TypeError, match="AspectGateHost"):
            validate_gate_hosts(cls, [_make_aspect("v"), _make_aspect("f", "summary")], [], [])

    def test_aspects_with_host_passes(self):
        cls = type("Good", (AspectGateHost,), {})
        validate_gate_hosts(cls, [_make_aspect("v")], [], [])

    def test_error_contains_aspect_names(self):
        cls = type("Bad", (), {})
        with pytest.raises(TypeError, match="step_one"):
            validate_gate_hosts(cls, [_make_aspect("step_one"), _make_aspect("step_two")], [], [])


class TestCheckerGateHostValidation:
    def test_checkers_without_host_raises(self):
        cls = type("Bad", (AspectGateHost,), {})
        with pytest.raises(TypeError, match="CheckerGateHost"):
            validate_gate_hosts(cls, [], [_make_checker("v", "amount")], [])

    def test_checkers_with_host_passes(self):
        cls = type("Good", (AspectGateHost, CheckerGateHost), {})
        validate_gate_hosts(cls, [], [_make_checker("v", "amount")], [])


class TestOnGateHostValidation:
    def test_subscriptions_without_host_raises(self):
        cls = type("Bad", (), {})
        with pytest.raises(TypeError, match="OnGateHost"):
            validate_gate_hosts(cls, [], [], [FakeSubscription("global_finish")])

    def test_subscriptions_with_host_passes(self):
        cls = type("Good", (OnGateHost,), {})
        validate_gate_hosts(cls, [], [], [FakeSubscription("global_finish")])


class TestSensitiveNoGateRequired:
    def test_no_gate_needed_for_empty(self):
        cls = type("DataModel", (), {})
        validate_gate_hosts(cls, [], [], [])


class TestEmptyClassNoValidation:
    def test_empty_class_passes(self):
        validate_gate_hosts(type("E", (), {}), [], [], [])


class TestBaseActionPassesAll:
    def test_all_hosts(self):
        cls = type("Full", (AspectGateHost, CheckerGateHost, OnGateHost), {})
        validate_gate_hosts(
            cls,
            [_make_aspect("v")],
            [_make_checker("v", "a")],
            [FakeSubscription("global_finish")],
        )
