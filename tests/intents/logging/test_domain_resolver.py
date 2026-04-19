# tests/intents/logging/test_domain_resolver.py
"""resolve_domain and domain_label."""

from __future__ import annotations

import pytest

from action_machine.domain.base_domain import BaseDomain
from action_machine.logging.domain_resolver import domain_label, resolve_domain


class _NoMeta:
    pass


class _MetaNoDomain:
    _meta_info = {"description": "d"}


class _OrdersTestDomain(BaseDomain):
    name = "orders"
    description = "Test domain for resolve_domain"


class _MetaDomainOk:
    _meta_info = {"domain": _OrdersTestDomain}


class _MetaDomainBad:
    _meta_info = {"domain": "not-a-domain"}


def test_resolve_domain_without_meta_returns_none() -> None:
    assert resolve_domain(_NoMeta) is None


def test_resolve_domain_meta_without_domain_key_returns_none() -> None:
    assert resolve_domain(_MetaNoDomain) is None


def test_resolve_domain_returns_subclass() -> None:
    d = resolve_domain(_MetaDomainOk)
    assert d is _OrdersTestDomain


def test_resolve_domain_invalid_domain_raises() -> None:
    with pytest.raises(TypeError, match="invalid domain"):
        resolve_domain(_MetaDomainBad)


def test_domain_label_none() -> None:
    assert domain_label(None) is None


def test_domain_label_uses_name_attr() -> None:
    class BillingDomain(BaseDomain):
        name = "billing"
        description = "Billing"

    assert domain_label(BillingDomain) == "billing"


def test_domain_label_falls_back_to_type_name_when_name_attr_absent() -> None:
    class _BareType:
        pass

    assert domain_label(_BareType) == "_BareType"  # type: ignore[arg-type]
