# tests/action_machine/dependencies/test_depends_mode_validation.py
"""PR-2: ``@depends(..., mode=...)`` validation matrix."""

import pytest

from aoa.action_machine.intents.depends import UseCase, depends
from aoa.action_machine.intents.depends.depends_intent import DependsIntent
from aoa.action_machine.model.base_action import BaseAction
from tests.support.domain_model.ping_action import PingAction
from tests.support.domain_model.services import PaymentServiceResource


class _PlainSvc:
    pass


def test_depends_rejects_mode_non_str() -> None:
    with pytest.raises(TypeError, match="mode"):
        depends(PingAction, mode=99, description="x")  # type: ignore[arg-type]


def test_depends_resource_with_mode_value_error() -> None:
    dec = depends(PaymentServiceResource, mode=UseCase.include, description="x")
    with pytest.raises(ValueError, match="resource dependencies must not set mode"):

        class _Host(DependsIntent[PaymentServiceResource]):
            pass

        dec(_Host)


def test_depends_action_without_mode_value_error() -> None:
    dec = depends(PingAction, description="peer")
    with pytest.raises(ValueError, match="require"):

        class _Host(DependsIntent[PingAction]):
            pass

        dec(_Host)


def test_depends_action_with_invalid_mode_string_value_error() -> None:
    dec = depends(PingAction, mode="bogus", description="peer")
    with pytest.raises(ValueError, match="require"):

        class _Host(DependsIntent[PingAction]):
            pass

        dec(_Host)


def test_depends_rejects_base_action_as_target() -> None:
    dec = depends(BaseAction, mode=UseCase.include, description="x")
    with pytest.raises(ValueError, match="concrete action"):

        class _Host(DependsIntent[BaseAction]):
            pass

        dec(_Host)


def test_depends_action_include_ok() -> None:
    @depends(PingAction, mode=UseCase.include, description="peer")
    class _Host(DependsIntent[PingAction]):
        pass

    assert _Host._depends_info[0].mode == UseCase.include
    assert _Host._depends_info[0].cls is PingAction


def test_depends_action_extend_ok() -> None:
    @depends(PingAction, mode=UseCase.extend, description="peer")
    class _Host(DependsIntent[PingAction]):
        pass

    assert _Host._depends_info[0].mode == UseCase.extend


def test_depends_plain_target_rejects_mode() -> None:
    dec = depends(_PlainSvc, mode=UseCase.include, description="x")
    with pytest.raises(ValueError, match="only valid for BaseAction"):

        class _Host(DependsIntent[_PlainSvc]):
            pass

        dec(_Host)


def test_depends_resource_without_mode_ok() -> None:
    @depends(PaymentServiceResource, description="pay")
    class _Host(DependsIntent[PaymentServiceResource]):
        pass

    assert _Host._depends_info[0].mode is None


def test_depends_resource_explicit_none_ok() -> None:
    @depends(PaymentServiceResource, mode=None, description="pay")
    class _Host(DependsIntent[PaymentServiceResource]):
        pass

    assert _Host._depends_info[0].mode is None
