# tests/dependencies/test_depends_decorator_validation.py
"""@depends decorator argument and target validation."""

import pytest

from action_machine.intents.depends import depends
from action_machine.intents.depends.depends_intent import DependsIntent


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


def test_depends_accepts_class_without_depends_intent_uses_object_bound() -> None:
    class Plain:
        pass

    dec = depends(_Svc, description="d")
    dec(Plain)
    assert Plain._depends_info[0].cls is _Svc


def test_depends_rejects_service_outside_bound() -> None:
    class Bound:
        pass

    class Other:
        pass

    class _Host(DependsIntent[Bound]):
        pass

    dec = depends(Other, description="x")
    with pytest.raises(TypeError, match="not a subclass of any allowed"):
        dec(_Host)


def test_depends_accepts_service_matching_union_branch() -> None:
    class BranchA:
        pass

    class BranchB:
        pass

    class ServiceA(BranchA):
        pass

    class ServiceB(BranchB):
        pass

    class _Host(DependsIntent[BranchA | BranchB]):
        pass

    depends(ServiceA, description="a")(_Host)
    depends(ServiceB, description="b")(_Host)
    assert {info.cls for info in _Host._depends_info} == {ServiceA, ServiceB}


def test_depends_rejects_service_outside_union_bound() -> None:
    class BranchA:
        pass

    class BranchB:
        pass

    class Other:
        pass

    class _Host(DependsIntent[BranchA | BranchB]):
        pass

    dec = depends(Other, description="x")
    with pytest.raises(TypeError, match="not a subclass of any allowed"):
        dec(_Host)


def test_depends_rejects_duplicate_registration() -> None:
    with pytest.raises(ValueError, match="already declared"):

        @depends(_Svc, description="a")
        @depends(_Svc, description="b")
        class _DupAction(DependsIntent[object]):
            pass
