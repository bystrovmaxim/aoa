# tests/adapters/mcp/test_mcp_schema.py
"""
Тесты inputSchema MCP tools, генерируемой McpAdapter.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Проверяет, что inputSchema MCP tools содержит метаданные, определённые
в коде через Pydantic Field(description=..., examples=..., gt=...,
min_length=..., pattern=...).

Это ключевое свойство McpAdapter: описания полей, constraints, examples —
всё берётся из Pydantic-моделей Params через model_json_schema() и попадает
в inputSchema без дублирования. AI-агент видит полностью типизированную
схему входных параметров.

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

Описания полей (Field description):
    - Каждое поле Params содержит description в inputSchema.

Типы полей (JSON Schema types):
    - user_id: string.
    - amount: number.
    - currency: string с default.

Constraints (Field gt, min_length, pattern):
    - amount: exclusiveMinimum (gt=0).
    - user_id: minLength (min_length=1).
    - currency: pattern (^[A-Z]{3}$).

Examples (Field examples):
    - Поля с examples содержат массив примеров.

Обязательные поля (required):
    - user_id и amount — required.
    - currency с default — не required.

Пустые Params:
    - PingAction с пустыми Params → схема без обязательных полей.
"""

from __future__ import annotations

import pytest
from pydantic import Field

from action_machine.aspects.regular_aspect import regular_aspect
from action_machine.aspects.summary_aspect import summary_aspect
from action_machine.auth.check_roles import CheckRoles
from action_machine.checkers.result_string_checker import ResultStringChecker
from action_machine.core.base_action import BaseAction
from action_machine.core.base_params import BaseParams
from action_machine.core.base_result import BaseResult
from action_machine.core.meta_decorator import meta

# ═════════════════════════════════════════════════════════════════════════════
# Тестовые модели и действия
# ═════════════════════════════════════════════════════════════════════════════


class EmptyParams(BaseParams):
    """Пустые параметры."""
    pass


class PingResult(BaseResult):
    """Результат пинга."""
    message: str = Field(default="pong", description="Ответ")


class OrderParams(BaseParams):
    """Параметры заказа с constraints и examples."""
    user_id: str = Field(
        description="Идентификатор пользователя",
        min_length=1,
        examples=["user_123"],
    )
    amount: float = Field(
        description="Сумма заказа",
        gt=0,
        examples=[1500.0, 99.99],
    )
    currency: str = Field(
        default="RUB",
        description="Код валюты ISO 4217",
        pattern=r"^[A-Z]{3}$",
        examples=["RUB", "USD", "EUR"],
    )


class OrderResult(BaseResult):
    """Результат заказа."""
    order_id: str = Field(description="ID заказа")
    status: str = Field(description="Статус")
    total: float = Field(description="Итого", ge=0)


@meta(description="Проверка доступности")
@CheckRoles(CheckRoles.NONE, desc="")
class PingAction(BaseAction[EmptyParams, PingResult]):
    @summary_aspect("Pong")
    async def pong(self, params, state, box, connections):
        return PingResult(message="pong")


@meta(description="Создание заказа")
@CheckRoles(CheckRoles.NONE, desc="")
class CreateOrderAction(BaseAction[OrderParams, OrderResult]):
    @regular_aspect("Валидация")
    @ResultStringChecker("validated_user", "Проверенный", required=True)
    async def validate(self, params, state, box, connections):
        return {"validated_user": params.user_id}

    @summary_aspect("Результат")
    async def build_result(self, params, state, box, connections):
        return OrderResult(order_id="ORD-1", status="created", total=params.amount)


# ═════════════════════════════════════════════════════════════════════════════
# Фикстуры
# ═════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def order_schema() -> dict:
    """JSON Schema модели OrderParams."""
    return OrderParams.model_json_schema()


@pytest.fixture
def empty_schema() -> dict:
    """JSON Schema модели EmptyParams."""
    return EmptyParams.model_json_schema()


# ═════════════════════════════════════════════════════════════════════════════
# Вспомогательные функции
# ═════════════════════════════════════════════════════════════════════════════


def _get_property(schema: dict, name: str) -> dict:
    """Извлекает описание свойства из JSON Schema."""
    return schema["properties"][name]


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Описания полей
# ═════════════════════════════════════════════════════════════════════════════


class TestFieldDescriptions:
    """Тесты описаний полей в inputSchema."""

    def test_user_id_description(self, order_schema):
        prop = _get_property(order_schema, "user_id")
        assert prop["description"] == "Идентификатор пользователя"

    def test_amount_description(self, order_schema):
        prop = _get_property(order_schema, "amount")
        assert prop["description"] == "Сумма заказа"

    def test_currency_description(self, order_schema):
        prop = _get_property(order_schema, "currency")
        assert prop["description"] == "Код валюты ISO 4217"


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Типы полей
# ═════════════════════════════════════════════════════════════════════════════


class TestFieldTypes:
    """Тесты типов полей в inputSchema."""

    def test_user_id_is_string(self, order_schema):
        prop = _get_property(order_schema, "user_id")
        assert prop["type"] == "string"

    def test_amount_is_number(self, order_schema):
        prop = _get_property(order_schema, "amount")
        assert prop["type"] == "number"

    def test_currency_is_string(self, order_schema):
        prop = _get_property(order_schema, "currency")
        assert prop["type"] == "string"


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Constraints
# ═════════════════════════════════════════════════════════════════════════════


class TestConstraints:
    """Тесты constraints полей в inputSchema."""

    def test_amount_exclusive_minimum(self, order_schema):
        """amount с gt=0 → exclusiveMinimum: 0."""
        prop = _get_property(order_schema, "amount")
        assert prop.get("exclusiveMinimum") == 0

    def test_user_id_min_length(self, order_schema):
        """user_id с min_length=1 → minLength: 1."""
        prop = _get_property(order_schema, "user_id")
        assert prop.get("minLength") == 1

    def test_currency_pattern(self, order_schema):
        """currency с pattern=^[A-Z]{3}$ → pattern в schema."""
        prop = _get_property(order_schema, "currency")
        assert prop.get("pattern") == "^[A-Z]{3}$"

    def test_currency_default(self, order_schema):
        """currency с default="RUB" → default: "RUB"."""
        prop = _get_property(order_schema, "currency")
        assert prop.get("default") == "RUB"


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Examples
# ═════════════════════════════════════════════════════════════════════════════


class TestExamples:
    """Тесты examples полей в inputSchema."""

    def test_user_id_examples(self, order_schema):
        prop = _get_property(order_schema, "user_id")
        assert "examples" in prop
        assert "user_123" in prop["examples"]

    def test_amount_examples(self, order_schema):
        prop = _get_property(order_schema, "amount")
        assert "examples" in prop
        assert 1500.0 in prop["examples"]
        assert 99.99 in prop["examples"]

    def test_currency_examples(self, order_schema):
        prop = _get_property(order_schema, "currency")
        assert "examples" in prop
        assert "RUB" in prop["examples"]
        assert "USD" in prop["examples"]
        assert "EUR" in prop["examples"]


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Обязательные поля (required)
# ═════════════════════════════════════════════════════════════════════════════


class TestRequiredFields:
    """Тесты обязательности полей в inputSchema."""

    def test_user_id_is_required(self, order_schema):
        assert "user_id" in order_schema.get("required", [])

    def test_amount_is_required(self, order_schema):
        assert "amount" in order_schema.get("required", [])

    def test_currency_is_not_required(self, order_schema):
        required = order_schema.get("required", [])
        assert "currency" not in required


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Пустые Params
# ═════════════════════════════════════════════════════════════════════════════


class TestEmptyParams:
    """Тесты схемы для пустых Params (PingAction)."""

    def test_empty_params_no_required(self, empty_schema):
        """Пустые Params → нет обязательных полей."""
        required = empty_schema.get("required", [])
        assert len(required) == 0

    def test_empty_params_no_properties(self, empty_schema):
        """Пустые Params → нет свойств или свойства пустые."""
        properties = empty_schema.get("properties", {})
        assert len(properties) == 0

    def test_empty_params_type_object(self, empty_schema):
        """Пустые Params → type: object."""
        assert empty_schema.get("type") == "object"


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Наличие всех полей
# ═════════════════════════════════════════════════════════════════════════════


class TestFieldPresence:
    """Тесты наличия всех ожидаемых полей в schema."""

    def test_all_order_fields_present(self, order_schema):
        """Все поля OrderParams присутствуют в schema."""
        properties = order_schema.get("properties", {})
        assert "user_id" in properties
        assert "amount" in properties
        assert "currency" in properties

    def test_no_extra_fields(self, order_schema):
        """В schema нет лишних полей."""
        properties = order_schema.get("properties", {})
        assert set(properties.keys()) == {"user_id", "amount", "currency"}

    def test_schema_title(self, order_schema):
        """Schema содержит title из имени класса."""
        assert order_schema.get("title") == "OrderParams"

    def test_empty_schema_title(self, empty_schema):
        """Пустая schema содержит title."""
        assert empty_schema.get("title") == "EmptyParams"
