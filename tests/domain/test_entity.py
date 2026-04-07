# tests/domain/test_entity.py
"""
Тесты для BaseEntity и @entity декоратора.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Проверяет:
- Создание сущностей через @entity
- Наследование от BaseEntity
- Frozen семантику
- Dict-like доступ
- Dot-path навигацию
- Сериализацию через model_dump
"""

import pytest
from pydantic import ValidationError

from action_machine.domain import BaseEntity, entity
from action_machine.domain.entity_decorator import EntityDecoratorError
from tests.domain_model.entities import SampleEntity, TestDomain


class TestEntityDecorator:
    """Тесты для @entity декоратора."""

    def test_valid_entity_creation(self):
        """Создание корректной сущности."""
        @entity(description="Тестовая сущность", domain=TestDomain)
        class ValidEntity(BaseEntity):
            id: str
            name: str

        assert hasattr(ValidEntity, "_entity_info")
        assert ValidEntity._entity_info["description"] == "Тестовая сущность"
        assert ValidEntity._entity_info["domain"] == TestDomain

    def test_missing_description(self):
        """Ошибка при отсутствии description."""
        with pytest.raises(EntityDecoratorError, match="description не может быть пустой"):
            @entity(description="", domain=TestDomain)
            class InvalidEntity(BaseEntity):
                id: str

    def test_invalid_domain(self):
        """Ошибка при некорректном domain."""
        with pytest.raises(EntityDecoratorError):
            @entity(description="Тест", domain="not_a_domain")
            class InvalidEntity(BaseEntity):
                id: str

    def test_no_inheritance_from_base_entity(self):
        """Ошибка при применении к классу не наследующему BaseEntity."""
        with pytest.raises(EntityDecoratorError):
            @entity(description="Тест")
            class InvalidEntity:
                id: str


class TestBaseEntity:
    """Тесты для BaseEntity."""

    def test_entity_creation(self):
        """Создание экземпляра сущности."""
        entity = SampleEntity(id="123", name="Test", value=42)
        assert entity.id == "123"
        assert entity.name == "Test"
        assert entity.value == 42

    def test_frozen_semantics(self):
        """Проверка неизменяемости (frozen=True)."""
        entity = SampleEntity(id="123", name="Test", value=42)

        with pytest.raises(ValidationError):
            entity.value = 100

    def test_dict_access(self):
        """Dict-like доступ к полям."""
        entity = SampleEntity(id="123", name="Test", value=42)

        assert entity["id"] == "123"
        assert "name" in entity
        assert entity["value"] == 42

    def test_model_dump(self):
        """Сериализация через model_dump."""
        entity = SampleEntity(id="123", name="Test", value=42)
        data = entity.model_dump()

        assert data == {"id": "123", "name": "Test", "value": 42}

    def test_validation(self):
        """Валидация полей."""
        # Корректные данные
        entity = SampleEntity(id="123", name="Test", value=42)
        assert entity.value == 42

        # Некорректные данные
        with pytest.raises(ValidationError):
            SampleEntity(id="123", name="Test", value=-1)  # value >= 0

    def test_extra_fields_forbid(self):
        """Запрет дополнительных полей (extra='forbid')."""
        with pytest.raises(ValidationError):
            SampleEntity(id="123", name="Test", value=42, extra_field="not_allowed")
