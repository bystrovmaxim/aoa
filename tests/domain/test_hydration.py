# tests/domain/test_hydration.py
"""
Тесты для hydration — сборки сущностей из данных.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Проверяет:
- Сборку сущностей через build()
- EntityProxy для типизированного доступа
- Обработку вложенных данных
- Валидацию при сборке
"""

import pytest
from pydantic import ValidationError

from action_machine.domain import build
from tests.domain_model.entities import RelatedEntity, SampleEntity


class TestBuildFunction:
    """Тесты для функции build()."""

    def test_build_simple_entity(self):
        """Сборка простой сущности."""
        data = {
            "id": "123",
            "name": "Test Entity",
            "value": 42,
        }

        entity = build(data, SampleEntity)

        assert isinstance(entity, SampleEntity)
        assert entity.id == "123"
        assert entity.name == "Test Entity"
        assert entity.value == 42

    def test_build_with_validation(self):
        """Сборка с валидацией данных."""
        # Корректные данные
        data = {"id": "123", "name": "Test", "value": 10}
        entity = build(data, SampleEntity)
        assert entity.value == 10

        # Некорректные данные
        data_invalid = {"id": "123", "name": "Test", "value": -1}
        with pytest.raises(ValidationError):
            build(data_invalid, SampleEntity)

    def test_build_with_relations(self):
        """Сборка сущности со связями — явная передача значений."""
        data = {
            "id": "parent-123",
            "title": "Parent Entity",
            "parent": None,
            "children": None,
        }

        entity = build(data, RelatedEntity)

        assert isinstance(entity, RelatedEntity)
        assert entity.id == "parent-123"
        assert entity.title == "Parent Entity"
        assert entity.parent is None
        assert entity.children is None

    def test_build_without_optional_relations(self):
        """Сборка без передачи связей — подставляется default Rel."""
        from action_machine.domain.relation_markers import Rel

        data = {
            "id": "parent-123",
            "title": "Parent Entity",
            "parent": None,
        }

        entity = build(data, RelatedEntity)

        assert entity.id == "parent-123"
        # children не передан → default Rel(description="...")
        assert isinstance(entity.children, Rel)

    def test_build_partial_data(self):
        """Сборка с неполными данными."""
        data = {"id": "123", "name": "Test"}
        # В TestEntity value обязательное — исключение
        with pytest.raises(ValidationError):
            build(data, SampleEntity)

    def test_build_extra_fields(self):
        """Сборка с лишними полями (extra='forbid')."""
        data = {
            "id": "123",
            "name": "Test",
            "value": 42,
            "extra_field": "not allowed",
        }

        with pytest.raises(ValidationError):
            build(data, SampleEntity)


class TestEntityProxy:
    """Тесты для EntityProxy (внутренний класс build)."""

    def test_proxy_creation(self):
        """Создание прокси для данных."""
        from action_machine.domain import BaseEntity
        from action_machine.domain.hydration import EntityProxy

        class DummyEntity(BaseEntity):
            field1: str
            field2: int

        proxy = EntityProxy(DummyEntity)

        assert proxy.field1 == "field1"
        assert proxy.field2 == "field2"

    def test_proxy_missing_field(self):
        """Доступ к отсутствующему полю."""
        from action_machine.domain import BaseEntity
        from action_machine.domain.hydration import EntityProxy

        class DummyEntity(BaseEntity):
            existing: str

        proxy = EntityProxy(DummyEntity)

        with pytest.raises(AttributeError):
            _ = proxy.missing_field

    def test_proxy_getattr(self):
        """Тестирование __getattr__ в прокси."""
        from action_machine.domain import BaseEntity
        from action_machine.domain.hydration import EntityProxy

        class DummyEntity(BaseEntity):
            test: str

        proxy = EntityProxy(DummyEntity)

        # Прямой доступ
        assert proxy.test == "test"
        # Через __getattr__
        assert proxy.__getattr__("test") == "test"
        # Отсутствующее поле
        with pytest.raises(AttributeError):
            proxy.__getattr__("missing")
