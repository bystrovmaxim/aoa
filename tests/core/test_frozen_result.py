# tests/core/test_frozen_result.py
"""
Тесты frozen-семантики BaseResult.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Проверяет, что BaseResult и его наследники полностью неизменяемы после
создания: запись атрибутов, добавление произвольных полей, dict-подобная
запись — всё запрещено. Произвольные поля запрещены (extra="forbid") [1].

Также проверяет корректность чтения через BaseSchema [2] и сериализацию
через pydantic model_dump() / model_json_schema().
"""

import pytest
from pydantic import Field, ValidationError

from action_machine.core.base_result import BaseResult

# ═════════════════════════════════════════════════════════════════════════════
# Тестовый наследник BaseResult
# ═════════════════════════════════════════════════════════════════════════════

class OrderResult(BaseResult):
    """Тестовый результат с тремя явно объявленными полями."""
    order_id: str = Field(description="ID заказа")
    status: str = Field(description="Статус заказа")
    total: float = Field(description="Итоговая сумма", ge=0)


class EmptyResult(BaseResult):
    """Тестовый результат без полей — для smoke-тестов."""
    pass


# ═════════════════════════════════════════════════════════════════════════════
# Создание и чтение
# ═════════════════════════════════════════════════════════════════════════════

class TestBaseResultCreation:
    """Тесты создания и чтения данных из BaseResult."""

    def test_create_with_fields(self) -> None:
        """Наследник BaseResult создаётся с явно объявленными полями."""
        result = OrderResult(order_id="ORD-1", status="created", total=1500.0)
        assert result.order_id == "ORD-1"
        assert result.status == "created"
        assert result.total == 1500.0

    def test_create_empty_result(self) -> None:
        """Пустой наследник BaseResult создаётся без ошибок."""
        result = EmptyResult()
        assert result.keys() == []

    def test_pydantic_validation(self) -> None:
        """Pydantic валидирует типы и constraints при создании."""
        with pytest.raises(ValidationError):
            OrderResult(order_id="ORD-1", status="created", total=-1.0)

    def test_getitem_access(self) -> None:
        """Dict-подобный доступ через квадратные скобки (BaseSchema)."""
        result = OrderResult(order_id="ORD-1", status="created", total=100.0)
        assert result["order_id"] == "ORD-1"
        assert result["status"] == "created"

    def test_getitem_missing_raises(self) -> None:
        """Обращение к несуществующему ключу бросает KeyError."""
        result = OrderResult(order_id="ORD-1", status="ok", total=0.0)
        with pytest.raises(KeyError):
            _ = result["nonexistent"]

    def test_get_with_default(self) -> None:
        """Метод get() возвращает default для отсутствующего ключа."""
        result = OrderResult(order_id="ORD-1", status="ok", total=0.0)
        assert result.get("order_id") == "ORD-1"
        assert result.get("missing") is None
        assert result.get("missing", "fallback") == "fallback"

    def test_contains(self) -> None:
        """Оператор in проверяет наличие ключа."""
        result = OrderResult(order_id="ORD-1", status="ok", total=0.0)
        assert "order_id" in result
        assert "missing" not in result

    def test_keys_values_items(self) -> None:
        """Методы keys, values, items возвращают корректные данные."""
        result = OrderResult(order_id="ORD-1", status="ok", total=50.0)
        assert set(result.keys()) == {"order_id", "status", "total"}
        assert "ORD-1" in result.values()
        assert ("status", "ok") in result.items()

    def test_resolve(self) -> None:
        """resolve() работает для плоских ключей."""
        result = OrderResult(order_id="ORD-1", status="ok", total=99.9)
        assert result.resolve("total") == 99.9
        assert result.resolve("missing") is None

    def test_model_dump(self) -> None:
        """model_dump() сериализует все объявленные поля."""
        result = OrderResult(order_id="ORD-1", status="ok", total=100.0)
        assert result.model_dump() == {"order_id": "ORD-1", "status": "ok", "total": 100.0}

    def test_model_json_schema(self) -> None:
        """model_json_schema() генерирует JSON Schema с descriptions."""
        schema = OrderResult.model_json_schema()
        props = schema.get("properties", {})
        assert "order_id" in props
        assert props["order_id"].get("description") == "ID заказа"


# ═════════════════════════════════════════════════════════════════════════════
# Frozen-семантика: запись запрещена
# ═════════════════════════════════════════════════════════════════════════════

class TestBaseResultFrozen:
    """Тесты неизменяемости BaseResult после создания."""

    def test_setattr_existing_raises(self) -> None:
        """Изменение существующего поля запрещено — ValidationError."""
        result = OrderResult(order_id="ORD-1", status="created", total=100.0)
        with pytest.raises(ValidationError):
            result.status = "paid"

    def test_setattr_new_field_raises(self) -> None:
        """Добавление нового атрибута запрещено — ValidationError (extra="forbid")."""
        result = OrderResult(order_id="ORD-1", status="ok", total=0.0)
        with pytest.raises((ValidationError, TypeError, AttributeError)):
            result.debug_info = "test"

    def test_extra_fields_forbidden_at_creation(self) -> None:
        """Произвольные поля при создании запрещены (extra="forbid")."""
        with pytest.raises(ValidationError):
            OrderResult(
                order_id="ORD-1",
                status="ok",
                total=0.0,
                unexpected_field="surprise",
            )

    def test_setitem_raises(self) -> None:
        """Dict-подобная запись через [] отсутствует (BaseResult frozen, __setitem__ не определён)."""
        result = OrderResult(order_id="ORD-1", status="ok", total=0.0)
        with pytest.raises((TypeError, AttributeError)):
            result["status"] = "new"

    def test_delitem_raises(self) -> None:
        """Dict-подобное удаление через del [] отсутствует."""
        result = OrderResult(order_id="ORD-1", status="ok", total=0.0)
        with pytest.raises((TypeError, AttributeError)):
            del result["status"]

    def test_write_method_missing(self) -> None:
        """Метод write() не существует (BaseResult не предоставляет запись)."""
        result = OrderResult(order_id="ORD-1", status="ok", total=0.0)
        assert not hasattr(result, "write")

    def test_update_method_missing(self) -> None:
        """Метод update() не существует (BaseResult не предоставляет запись)."""
        result = OrderResult(order_id="ORD-1", status="ok", total=0.0)
        assert not hasattr(result, "update")


# ═════════════════════════════════════════════════════════════════════════════
# Паттерн «изменения» — model_copy
# ═════════════════════════════════════════════════════════════════════════════

class TestBaseResultImmutableUpdate:
    """Тесты паттерна обновления через model_copy (pydantic)."""

    def test_model_copy_creates_new_instance(self) -> None:
        """model_copy(update=...) создаёт новый frozen-экземпляр."""
        original = OrderResult(order_id="ORD-1", status="created", total=100.0)
        updated = original.model_copy(update={"status": "paid"})
        assert updated.status == "paid"
        assert updated.order_id == "ORD-1"
        assert updated.total == 100.0
        assert original.status == "created"

    def test_model_copy_is_different_object(self) -> None:
        """model_copy возвращает новый объект, не ссылку на старый."""
        original = OrderResult(order_id="ORD-1", status="ok", total=0.0)
        copy = original.model_copy()
        assert copy is not original
        assert copy.model_dump() == original.model_dump()

    def test_model_copy_result_is_also_frozen(self) -> None:
        """Результат model_copy тоже frozen — запись запрещена."""
        original = OrderResult(order_id="ORD-1", status="ok", total=0.0)
        copy = original.model_copy(update={"status": "paid"})
        with pytest.raises(ValidationError):
            copy.status = "refunded"
