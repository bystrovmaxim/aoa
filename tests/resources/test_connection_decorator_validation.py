# tests/resources/test_connection_decorator_validation.py
"""@connection argument and target validation."""

import pytest

from action_machine.resources.base_resource_manager import BaseResourceManager
from action_machine.resources.connection_decorator import _validate_connection_args, connection
from action_machine.resources.connection_intent import ConnectionIntent


class _Mgr(BaseResourceManager):
    def get_wrapper_class(self):
        return None


class _NotManager:
    pass


def test_validate_connection_args_rejects_non_class_manager() -> None:
    with pytest.raises(TypeError, match="ожидает класс"):
        _validate_connection_args("mgr", "db", "d")  # type: ignore[arg-type]


def test_validate_connection_args_rejects_non_resource_manager() -> None:
    with pytest.raises(TypeError, match="BaseResourceManager"):
        _validate_connection_args(_NotManager, "db", "d")


def test_validate_connection_args_rejects_non_str_key() -> None:
    with pytest.raises(TypeError, match="key"):
        _validate_connection_args(_Mgr, 99, "d")  # type: ignore[arg-type]


def test_validate_connection_args_rejects_blank_key() -> None:
    with pytest.raises(ValueError, match="key"):
        _validate_connection_args(_Mgr, "   ", "d")


def test_validate_connection_args_rejects_non_str_description() -> None:
    with pytest.raises(TypeError, match="description"):
        _validate_connection_args(_Mgr, "db", 1)  # type: ignore[arg-type]


def test_connection_inner_rejects_non_class_target() -> None:
    dec = connection(_Mgr, key="db", description="x")
    with pytest.raises(TypeError, match="только к классу"):
        dec(99)  # type: ignore[arg-type]


def test_connection_inner_rejects_without_connection_intent() -> None:
    class Plain:
        pass

    dec = connection(_Mgr, key="db", description="x")
    with pytest.raises(TypeError, match="ConnectionIntent"):
        dec(Plain)


def test_connection_rejects_duplicate_key() -> None:
    with pytest.raises(ValueError, match="уже объявлен"):

        @connection(_Mgr, key="db", description="a")
        @connection(_Mgr, key="db", description="b")
        class _DupConn(ConnectionIntent):
            pass
