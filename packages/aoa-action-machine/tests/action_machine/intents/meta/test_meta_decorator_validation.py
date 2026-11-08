# tests/intents/meta/test_meta_decorator_validation.py
"""Internal @meta validation helpers (description, domain, target)."""

import pytest

from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.meta.meta_decorator import (
    _validate_meta_description,
    _validate_meta_domain,
    _validate_meta_target,
    meta,
)
from aoa.action_machine.model.base_action import BaseAction
from aoa.action_machine.model.stub_params import StubParams
from aoa.action_machine.model.stub_result import StubResult
from aoa.action_machine.resources import BaseController


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
    class SomeAction(BaseAction[StubParams, StubResult]):
        pass

    _validate_meta_target(SomeAction)


def test_validate_meta_target_accepts_plain_class() -> None:
    class Plain:
        pass

    _validate_meta_target(Plain)


def test_meta_decorator_attaches_meta_info_on_resource_manager() -> None:
    """A resource takes no domain: its ``_meta_info`` names only the description."""
    @meta(description="resource meta")
    class _MetaResourceController(BaseController):
        @classmethod
        def get_wrapper_class(cls):
            return None

    assert _MetaResourceController._meta_info == {
        "description": "resource meta",
        "domain": None,
    }


def test_meta_refuses_a_domain_on_a_resource() -> None:
    """A resource is a database shared by domains; ``domain=`` on it is refused by name."""
    with pytest.raises(TypeError, match="resource is a database shared by domains and takes no domain"):

        @meta(description="resource with a domain", domain=_OrdersDomain)
        class _DomainResourceController(BaseController):
            @classmethod
            def get_wrapper_class(cls):
                return None


def test_meta_still_requires_a_domain_on_a_non_resource_host() -> None:
    """Every host but a resource keeps its mandatory domain."""

    class Plain:
        pass

    with pytest.raises(TypeError, match="domain is required"):
        meta(description="plain host")(Plain)


def test_meta_still_attaches_the_domain_on_a_non_resource_host() -> None:
    """An action keeps the domain it declares, exactly as before."""

    class Plain:
        pass

    meta(description="plain host", domain=_OrdersDomain)(Plain)
    assert Plain._meta_info == {"description": "plain host", "domain": _OrdersDomain}
