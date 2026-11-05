# tests/domain/test_entity_intent_validators.py
"""entity_intent validators used by @entity / graph inspection."""

from __future__ import annotations

import pytest

from aoa.action_machine.domain.exceptions import EntityDecoratorError
from aoa.action_machine.intents.entity.entity_decorator import (
    validate_entity_decorator_target,
    validate_entity_description,
)


def test_validate_entity_description_rejects_non_str() -> None:
    with pytest.raises(EntityDecoratorError, match="must be str"):
        validate_entity_description(99)


def test_validate_entity_description_rejects_blank() -> None:
    with pytest.raises(EntityDecoratorError, match="cannot be empty"):
        validate_entity_description("   ")


def test_validate_entity_decorator_target_rejects_non_class() -> None:
    with pytest.raises(EntityDecoratorError, match="only to a class"):
        validate_entity_decorator_target(object())


def test_validate_entity_decorator_target_accepts_plain_class() -> None:
    class Plain:
        pass

    validate_entity_decorator_target(Plain)
