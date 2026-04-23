# tests/intents/meta/test_meta_decorator_validation.py
"""Internal @meta validation helpers (description, domain, target)."""

import pytest

from action_machine.domain.base_domain import BaseDomain
from action_machine.intents.meta.meta_decorator import (
    _validate_meta_description,
    _validate_meta_domain,
    _validate_meta_target,
    meta,
)
from action_machine.model.base_action import BaseAction
from action_machine.model.base_params import BaseParams
from action_machine.model.base_result import BaseResult
from action_machine.resources.base_resource import BaseResource


class _OrdersDomain(BaseDomain):
    name = "orders"
    description = "Orders"


def test_validate_meta_description_rejects_non_str() -> None:
    with pytest.raises(TypeError, match="description must be str"):
        _validate_meta_description(42)


def test_validate_meta_description_rejects_blank() -> None:
    with pytest.raises(ValueError, match="cannot be empty"):
        _validate_meta_description("   ")


def test_validate_meta_domain_requires_non_none() -> None:
    with pytest.raises(TypeError, match="domain is required"):
        _validate_meta_domain(None)


def test_validate_meta_domain_rejects_non_type() -> None:
    with pytest.raises(TypeError, match="must be a BaseDomain subclass"):
        _validate_meta_domain("OrdersDomain")


def test_validate_meta_domain_rejects_non_subclass() -> None:
    class NotDomain:
        pass

    with pytest.raises(TypeError, match="is not"):
        _validate_meta_domain(NotDomain)


def test_validate_meta_target_rejects_non_class() -> None:
    with pytest.raises(TypeError, match="only to classes"):
        _validate_meta_target(object())


def test_validate_meta_target_accepts_base_action_subclass() -> None:
    class SomeAction(BaseAction[BaseParams, BaseResult]):
        pass

    _validate_meta_target(SomeAction)


def test_validate_meta_target_accepts_plain_class() -> None:
    class Plain:
        pass

    _validate_meta_target(Plain)


def test_meta_decorator_attaches_meta_info_on_resource_manager() -> None:
    @meta(description="resource meta", domain=_OrdersDomain)
    class _MetaResourceManager(BaseResource):
        def get_wrapper_class(self):
            return None

    assert _MetaResourceManager._meta_info == {
        "description": "resource meta",
        "domain": _OrdersDomain,
    }
