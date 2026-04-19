# tests/domain/test_entity_intent_validators.py
"""entity_intent validators used by @entity / graph inspection."""

from __future__ import annotations

import pytest

from action_machine.domain.base_domain import BaseDomain
from action_machine.intents.domain.entity_intent import (
    EntityIntent,
    validate_entity_decorator_target,
    validate_entity_description,
    validate_entity_domain,
)
from action_machine.domain.exceptions import EntityDecoratorError


class _ShopDomain(BaseDomain):
    name = "shop"
    description = "Shop"


def test_validate_entity_description_rejects_non_str() -> None:
    with pytest.raises(EntityDecoratorError, match="must be str"):
        validate_entity_description(99)


def test_validate_entity_description_rejects_blank() -> None:
    with pytest.raises(EntityDecoratorError, match="cannot be empty"):
        validate_entity_description("   ")


def test_validate_entity_domain_none_is_ok() -> None:
    validate_entity_domain(None)


def test_validate_entity_domain_rejects_non_type() -> None:
    with pytest.raises(EntityDecoratorError, match="subclass or None"):
        validate_entity_domain("ShopDomain")


def test_validate_entity_domain_rejects_non_subclass() -> None:
    class NotDomain:
        pass

    with pytest.raises(EntityDecoratorError, match="inherit BaseDomain"):
        validate_entity_domain(NotDomain)


def test_validate_entity_domain_accepts_subclass() -> None:
    validate_entity_domain(_ShopDomain)


def test_validate_entity_decorator_target_rejects_non_class() -> None:
    with pytest.raises(EntityDecoratorError, match="only to a class"):
        validate_entity_decorator_target(object())


def test_validate_entity_decorator_target_rejects_without_entity_intent() -> None:
    class Plain:
        pass

    with pytest.raises(EntityDecoratorError, match="EntityIntent"):
        validate_entity_decorator_target(Plain)


def test_validate_entity_decorator_target_accepts_entity_intent_subclass() -> None:
    class OrderEntity(EntityIntent):
        pass

    validate_entity_decorator_target(OrderEntity)
