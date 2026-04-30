# tests/intents/meta/test_meta_intent_resolver.py
"""Meta intent resolver behavior."""

import pytest

from action_machine.domain.base_domain import BaseDomain
from action_machine.exceptions import MissingMetaError
from action_machine.intents.meta.meta_decorator import meta
from action_machine.intents.meta.meta_intent_resolver import MetaIntentResolver


class _BillingDomain(BaseDomain):
    name = "billing"
    description = "Billing"


@meta(description="Charge customer", domain=_BillingDomain)
class _MetaHost:
    pass


class _PlainHost:
    pass


def test_resolve_domain_type_returns_meta_domain() -> None:
    assert MetaIntentResolver.resolve_domain_type(_MetaHost) is _BillingDomain


def test_resolve_domain_type_raises_without_meta() -> None:
    with pytest.raises(MissingMetaError) as ei:
        MetaIntentResolver.resolve_domain_type(_PlainHost)
    assert ei.value.key == "domain"


def test_resolve_description_returns_meta_description() -> None:
    assert MetaIntentResolver.resolve_description(_MetaHost) == "Charge customer"


def test_resolve_description_raises_without_meta() -> None:
    with pytest.raises(MissingMetaError) as ei:
        MetaIntentResolver.resolve_description(_PlainHost)
    assert ei.value.key == "description"
