# tests/dependencies/test_depends_decorator_validation.py
"""@depends decorator argument and target validation."""

import pytest

from action_machine.legacy.dependency_intent import DependencyIntent
from action_machine.intents.depends import depends


class _Svc:
    pass


def test_depends_rejects_non_class_service() -> None:
    with pytest.raises(TypeError, match="expects a class"):
        depends("not-a-class", description="d")  # type: ignore[arg-type]


def test_depends_rejects_non_str_description() -> None:
    with pytest.raises(TypeError, match="description"):
        depends(_Svc, description=99)  # type: ignore[arg-type]


def test_depends_inner_rejects_non_class_target() -> None:
    dec = depends(_Svc, description="d")
    with pytest.raises(TypeError, match="only be applied to a class"):
        dec(42)  # type: ignore[arg-type]


def test_depends_inner_rejects_without_dependency_intent() -> None:
    class Plain:
        pass

    dec = depends(_Svc, description="d")
    with pytest.raises(TypeError, match="DependencyIntent"):
        dec(Plain)


def test_depends_rejects_service_outside_bound() -> None:
    class Bound:
        pass

    class Other:
        pass

    class _Host(DependencyIntent[Bound]):
        pass

    dec = depends(Other, description="x")
    with pytest.raises(TypeError, match="is not a subclass of"):
        dec(_Host)


def test_depends_rejects_duplicate_registration() -> None:
    with pytest.raises(ValueError, match="already declared"):

        @depends(_Svc, description="a")
        @depends(_Svc, description="b")
        class _DupAction(DependencyIntent[object]):
            pass
