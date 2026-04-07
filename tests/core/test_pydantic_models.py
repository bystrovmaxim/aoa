# tests/core/test_pydantic_models.py
"""
Тесты интеграции pydantic BaseModel с BaseParams, BaseResult и метаданными.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

BaseParams и BaseResult наследуют pydantic BaseModel (через BaseSchema),
что обеспечивает:

1. Валидация типов при создании экземпляра — передача str в int-поле
   вызывает ValidationError.
2. Constraints через Field(gt=0, min_length=3, pattern=...) — проверяются
   при создании и отображаются в JSON Schema.
3. Описания полей через Field(description="...") — попадают в JSON Schema,
   OpenAPI-документацию и ClassMetadata.params_fields/result_fields.
4. JSON Schema через model_json_schema() — используется FastAPI для
   автоматической генерации OpenAPI и MCP-адаптером для inputSchema.

BaseParams: frozen=True (неизменяемый после создания). BaseSchema
обеспечивает dict-подобное чтение и dot-path навигацию.

BaseResult: frozen=True, extra="forbid". Неизменяемый результат со строгой
структурой. Запись запрещена, произвольные поля запрещены.

BaseState: pydantic с extra="allow", динамические поля, frozen.
Покрыт в test_base_state.py и test_frozen_state.py.

DescribedFieldsGateHost: маркерный миксин, обозначающий обязательность
описания каждого поля через Field(description="..."). MetadataBuilder
проверяет при сборке ClassMetadata.

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

BaseParams (pydantic, frozen):
    - Создание с валидными данными.
    - Frozen: изменение поля → ValidationError.
    - Валидация типов: неверный тип → ValidationError.
    - Constraints: gt, min_length, max_length, pattern.
    - Default-значения полей.
    - Пустые Params (без полей) — валидны.
    - BaseSchema: keys, values, items, getitem, contains, get.
    - resolve() на pydantic-полях.

BaseResult (pydantic, frozen, extra="forbid"):
    - Создание и чтение полей.
    - Frozen: изменение через setattr → ValidationError.
    - Frozen: изменение через __setitem__ → TypeError (нет метода).
    - Extra-поля запрещены (extra="forbid").
    - Constraints: ge и другие.
    - BaseSchema: keys работает только для объявленных полей.
    - Пустой Result — валиден.

JSON Schema:
    - descriptions из Field(description=...) в schema.
    - constraints (exclusiveMinimum, minLength и т.д.) в schema.
    - examples из Field(examples=[...]) в schema.

Валидация описаний (DescribedFieldsGateHost):
    - Все поля с описанием → OK.
    - Поле без description → TypeError при сборке метаданных.
    - Поле с пустым description → TypeError.
    - Пустые модели (без полей) → OK, без ошибок.

ClassMetadata — params_fields и result_fields:
    - params_fields содержит описания, constraints, examples.
    - result_fields содержит описания и constraints.
    - FieldDescriptionMeta.required и default корректны.
    - FieldDescriptionMeta.field_type — строковое представление типа.

BaseState (pydantic, extra="allow", frozen):
    - Создание через kwargs.
    - Динамические поля.
    - to_dict() и resolve().
    - Отсутствие write/update.
"""

import pytest
from pydantic import Field, ValidationError

from action_machine.aspects.summary_aspect import summary_aspect
from action_machine.auth import ROLE_NONE, check_roles
from action_machine.core.base_action import BaseAction
from action_machine.core.base_params import BaseParams
from action_machine.core.base_result import BaseResult
from action_machine.core.base_state import BaseState
from action_machine.core.gate_coordinator import GateCoordinator
from action_machine.core.meta_decorator import meta
from tests.domain_model import FullAction, PingAction, SimpleAction

# ═════════════════════════════════════════════════════════════════════════════
# Вспомогательные модели для edge-case тестов
# ═════════════════════════════════════════════════════════════════════════════


class OrderParams(BaseParams):
    """Параметры заказа — все поля с описанием и constraints."""
    user_id: str = Field(
        description="Идентификатор пользователя",
        examples=["user_123"],
    )
    amount: float = Field(
        description="Сумма заказа в рублях",
        gt=0,
    )
    currency: str = Field(
        default="RUB",
        description="Код валюты ISO 4217",
        min_length=3,
        max_length=3,
    )
    comment: str | None = Field(
        default=None,
        description="Комментарий к заказу",
    )


class OrderResult(BaseResult):
    """Результат заказа — все поля с описанием."""
    order_id: str = Field(description="Идентификатор заказа")
    status: str = Field(
        description="Статус заказа",
        examples=["created", "pending"],
    )
    total: float = Field(description="Итоговая сумма", ge=0)


class EmptyParams(BaseParams):
    """Пустые параметры — допустимы для действий без входных данных."""
    pass


class EmptyResult(BaseResult):
    """Пустой результат — допустим для действий без выходных данных."""
    pass


class BadParamsNoDescription(BaseParams):
    """Параметры с полем без description — для теста ошибки валидации."""
    user_id: str  # нет Field(description="...")


class BadParamsEmptyDescription(BaseParams):
    """Параметры с пустым description — для теста ошибки валидации."""
    user_id: str = Field(description="")


class BadResultNoDescription(BaseResult):
    """Результат с полем без description — для теста ошибки валидации."""
    order_id: str  # нет Field(description="...")


# ═════════════════════════════════════════════════════════════════════════════
# Вспомогательные действия для MetadataBuilder
# ═════════════════════════════════════════════════════════════════════════════


@meta(description="Действие с полностью описанными Params и Result")
@check_roles(ROLE_NONE)
class GoodAction(BaseAction[OrderParams, OrderResult]):
    """Все поля Params и Result имеют description — проходит валидацию."""
    @summary_aspect("Создание заказа")
    async def finalize_summary(self, params, state, box, connections):
        return OrderResult(order_id="ORD-1", status="created", total=params.amount)


@meta(description="Действие с пустыми моделями")
@check_roles(ROLE_NONE)
class EmptyModelsAction(BaseAction[EmptyParams, EmptyResult]):
    """Пустые Params и Result — нет полей для проверки, проходит валидацию."""
    @summary_aspect("Пустой результат")
    async def finalize_summary(self, params, state, box, connections):
        return EmptyResult()


@meta(description="Действие с Params без description")
@check_roles(ROLE_NONE)
class BadParamsAction(BaseAction[BadParamsNoDescription, OrderResult]):
    """Поле user_id в Params без description — TypeError при сборке."""
    @summary_aspect("Результат")
    async def finalize_summary(self, params, state, box, connections):
        return OrderResult(order_id="ORD-1", status="ok", total=100.0)


@meta(description="Действие с пустым description в Params")
@check_roles(ROLE_NONE)
class BadParamsEmptyDescAction(BaseAction[BadParamsEmptyDescription, OrderResult]):
    """Пустая строка description — тоже ошибка."""
    @summary_aspect("Результат")
    async def finalize_summary(self, params, state, box, connections):
        return OrderResult(order_id="ORD-1", status="ok", total=100.0)


@meta(description="Действие с Result без description")
@check_roles(ROLE_NONE)
class BadResultAction(BaseAction[OrderParams, BadResultNoDescription]):
    """Поле order_id в Result без description — TypeError при сборке."""
    @summary_aspect("Результат")
    async def finalize_summary(self, params, state, box, connections):
        return BadResultNoDescription(order_id="ORD-1")


# ═════════════════════════════════════════════════════════════════════════════
# BaseParams — pydantic поведение
# ═════════════════════════════════════════════════════════════════════════════


class TestBaseParamsPydantic:
    """Pydantic-поведение BaseParams: валидация, frozen, constraints."""

    def test_create_with_valid_data(self) -> None:
        """
        Создание OrderParams с валидными данными — все поля заполнены.
        Pydantic валидирует типы и constraints при создании экземпляра.
        """
        # Arrange — валидные данные для всех обязательных полей
        # Act — pydantic проверяет типы и constraints в __init__
        params = OrderParams(user_id="user_123", amount=1500.0)

        # Assert — все поля доступны, default-значения применены
        assert params.user_id == "user_123"
        assert params.amount == 1500.0
        assert params.currency == "RUB"
        assert params.comment is None

    def test_frozen_prevents_modification(self) -> None:
        """
        frozen=True: попытка изменить поле → ValidationError.
        """
        # Arrange — созданный frozen-экземпляр
        params = OrderParams(user_id="user_123", amount=1500.0)

        # Act & Assert
        with pytest.raises(ValidationError):
            params.user_id = "other_user"

    def test_type_validation_rejects_wrong_type(self) -> None:
        """
        Передача неверного типа → ValidationError.
        """
        # Arrange & Act & Assert — неверные типы
        with pytest.raises(ValidationError):
            OrderParams(user_id=123, amount="not_a_number")

    def test_constraint_gt_zero(self) -> None:
        """
        Constraint gt=0: amount должен быть строго больше нуля.
        """
        # Arrange & Act & Assert — amount=0, нарушает gt=0
        with pytest.raises(ValidationError):
            OrderParams(user_id="u1", amount=0)

        # Arrange & Act & Assert — amount=-100
        with pytest.raises(ValidationError):
            OrderParams(user_id="u1", amount=-100)

    def test_constraint_min_max_length(self) -> None:
        """
        Constraints min_length=3, max_length=3 для currency.
        """
        # Arrange & Act & Assert — 2 символа
        with pytest.raises(ValidationError):
            OrderParams(user_id="u1", amount=100, currency="US")

        # Arrange & Act & Assert — 4 символа
        with pytest.raises(ValidationError):
            OrderParams(user_id="u1", amount=100, currency="EURO")

    def test_default_values_applied(self) -> None:
        """
        Поля с default получают значения по умолчанию при создании.
        """
        # Arrange & Act — создание без optional-полей
        params = OrderParams(user_id="u1", amount=100.0)

        # Assert
        assert params.currency == "RUB"
        assert params.comment is None

    def test_empty_params_valid(self) -> None:
        """
        Пустые BaseParams без полей — валидны.
        """
        # Arrange & Act
        params = EmptyParams()

        # Assert
        assert isinstance(params, BaseParams)


# ═════════════════════════════════════════════════════════════════════════════
# BaseParams — BaseSchema совместимость
# ═════════════════════════════════════════════════════════════════════════════


class TestBaseParamsBaseSchema:
    """BaseSchema работает на pydantic BaseParams."""

    def test_getitem(self) -> None:
        """
        params["user_id"] — dict-подобный доступ через BaseSchema.
        """
        # Arrange
        params = OrderParams(user_id="u1", amount=500.0)

        # Act & Assert
        assert params["user_id"] == "u1"
        assert params["amount"] == 500.0

    def test_getitem_missing_raises_key_error(self) -> None:
        """
        params["nonexistent"] → KeyError.
        """
        # Arrange
        params = OrderParams(user_id="u1", amount=500.0)

        # Act & Assert
        with pytest.raises(KeyError):
            _ = params["nonexistent"]

    def test_contains(self) -> None:
        """
        "user_id" in params → True. "nonexistent" in params → False.
        """
        # Arrange
        params = OrderParams(user_id="u1", amount=500.0)

        # Act & Assert
        assert "user_id" in params
        assert "amount" in params
        assert "nonexistent" not in params

    def test_get_with_default(self) -> None:
        """
        params.get("key", default) — безопасное чтение.
        """
        # Arrange
        params = OrderParams(user_id="u1", amount=500.0)

        # Act & Assert
        assert params.get("user_id") == "u1"
        assert params.get("nonexistent", "fallback") == "fallback"

    def test_keys_returns_model_fields(self) -> None:
        """
        keys() возвращает только объявленные поля pydantic-модели.
        BaseSchema.keys() использует model_fields.keys().
        """
        # Arrange
        params = OrderParams(user_id="u1", amount=500.0)

        # Act
        keys = params.keys()

        # Assert — четыре объявленных поля модели
        assert "user_id" in keys
        assert "amount" in keys
        assert "currency" in keys
        assert "comment" in keys
        assert len(keys) == 4

    def test_values_returns_field_values(self) -> None:
        """
        values() возвращает значения объявленных полей.
        """
        # Arrange
        params = OrderParams(user_id="u1", amount=500.0)

        # Act
        values = params.values()

        # Assert
        assert "u1" in values
        assert 500.0 in values
        assert "RUB" in values

    def test_items_returns_field_pairs(self) -> None:
        """
        items() возвращает пары (ключ, значение) для объявленных полей.
        """
        # Arrange
        params = OrderParams(user_id="u1", amount=500.0)

        # Act
        items = params.items()

        # Assert
        assert ("user_id", "u1") in items
        assert ("amount", 500.0) in items
        assert ("currency", "RUB") in items

    def test_resolve_flat_field(self) -> None:
        """
        resolve() работает для плоских полей pydantic-модели.
        Используется в шаблонах логирования: {%params.amount}.
        """
        # Arrange
        params = OrderParams(user_id="u1", amount=1500.0)

        # Act & Assert
        assert params.resolve("user_id") == "u1"
        assert params.resolve("amount") == 1500.0
        assert params.resolve("currency") == "RUB"

    def test_resolve_missing_returns_default(self) -> None:
        """
        resolve("nonexistent") на pydantic-модели возвращает default.
        """
        # Arrange
        params = OrderParams(user_id="u1", amount=500.0)

        # Act & Assert
        assert params.resolve("nonexistent", default="N/A") == "N/A"

    def test_resolve_none_field(self) -> None:
        """
        resolve("comment") возвращает None когда поле = None.
        """
        # Arrange — comment не передан, default=None
        params = OrderParams(user_id="u1", amount=500.0)

        # Act
        result = params.resolve("comment")

        # Assert — None из поля, не default
        assert result is None


# ═════════════════════════════════════════════════════════════════════════════
# BaseResult — pydantic поведение (frozen, extra="forbid")
# ═════════════════════════════════════════════════════════════════════════════


class TestBaseResultPydantic:
    """Pydantic-поведение BaseResult: frozen, extra="forbid", constraints."""

    def test_create_and_read(self) -> None:
        """
        Создание OrderResult и чтение полей.
        """
        # Arrange & Act
        result = OrderResult(order_id="ORD-1", status="created", total=1500.0)

        # Assert
        assert result.order_id == "ORD-1"
        assert result.status == "created"
        assert result.total == 1500.0

    def test_frozen_prevents_setattr(self) -> None:
        """
        BaseResult frozen=True — поля нельзя изменить через setattr.
        """
        # Arrange
        result = OrderResult(order_id="ORD-1", status="created", total=1500.0)

        # Act & Assert
        with pytest.raises(ValidationError):
            result.status = "paid"

    def test_no_setitem_method(self) -> None:
        """
        BaseResult не имеет __setitem__ — dict-подобная запись запрещена.
        """
        # Arrange
        result = OrderResult(order_id="ORD-1", status="created", total=1500.0)

        # Act & Assert
        with pytest.raises((TypeError, AttributeError)):
            result["status"] = "shipped"

    def test_extra_fields_forbidden_at_creation(self) -> None:
        """
        extra="forbid": передача лишнего поля при создании → ValidationError.
        """
        # Arrange & Act & Assert
        with pytest.raises(ValidationError):
            OrderResult(
                order_id="ORD-1",
                status="created",
                total=1500.0,
                unexpected_field="surprise",
            )

    def test_extra_fields_forbidden_after_creation(self) -> None:
        """
        extra="forbid": добавление нового поля после создания запрещено.
        """
        # Arrange
        result = OrderResult(order_id="ORD-1", status="created", total=1500.0)

        # Act & Assert
        with pytest.raises((ValidationError, TypeError, AttributeError)):
            result.debug_info = "extra"

    def test_constraint_ge_zero(self) -> None:
        """
        Constraint ge=0 на total: допускается 0 и выше.
        """
        # Arrange & Act & Assert — total=-10 нарушает ge=0
        with pytest.raises(ValidationError):
            OrderResult(order_id="ORD-1", status="fail", total=-10.0)

    def test_keys_returns_only_declared_fields(self) -> None:
        """
        keys() возвращает только объявленные поля модели.
        """
        # Arrange
        result = OrderResult(order_id="ORD-1", status="created", total=1500.0)

        # Act
        keys = result.keys()

        # Assert — только три объявленных поля
        assert set(keys) == {"order_id", "status", "total"}

    def test_empty_result_valid(self) -> None:
        """
        Пустой BaseResult без полей — валиден.
        """
        # Arrange & Act
        result = EmptyResult()

        # Assert
        assert isinstance(result, BaseResult)


# ═════════════════════════════════════════════════════════════════════════════
# JSON Schema
# ═════════════════════════════════════════════════════════════════════════════


class TestJsonSchema:
    """Генерация JSON Schema через pydantic model_json_schema()."""

    def test_params_schema_has_descriptions(self) -> None:
        """
        model_json_schema() содержит описания полей из Field(description=...).
        """
        # Arrange & Act
        schema = OrderParams.model_json_schema()
        props = schema["properties"]

        # Assert
        assert props["user_id"]["description"] == "Идентификатор пользователя"
        assert props["amount"]["description"] == "Сумма заказа в рублях"
        assert props["currency"]["description"] == "Код валюты ISO 4217"

    def test_params_schema_has_constraints(self) -> None:
        """
        JSON Schema содержит ограничения из Field(gt=0, min_length=3 и т.д.).
        """
        # Arrange & Act
        schema = OrderParams.model_json_schema()
        props = schema["properties"]

        # Assert
        assert props["amount"].get("exclusiveMinimum") == 0
        assert props["currency"].get("minLength") == 3
        assert props["currency"].get("maxLength") == 3

    def test_params_schema_has_examples(self) -> None:
        """
        JSON Schema содержит примеры из Field(examples=[...]).
        """
        # Arrange & Act
        schema = OrderParams.model_json_schema()
        props = schema["properties"]

        # Assert
        assert "examples" in props["user_id"]
        assert "user_123" in props["user_id"]["examples"]

    def test_result_schema_has_descriptions(self) -> None:
        """
        JSON Schema для Result содержит описания полей.
        """
        # Arrange & Act
        schema = OrderResult.model_json_schema()
        props = schema["properties"]

        # Assert
        assert props["order_id"]["description"] == "Идентификатор заказа"
        assert props["total"]["description"] == "Итоговая сумма"

    def test_result_schema_has_examples(self) -> None:
        """
        JSON Schema для Result содержит примеры.
        """
        # Arrange & Act
        schema = OrderResult.model_json_schema()
        props = schema["properties"]

        # Assert
        assert "examples" in props["status"]
        assert "created" in props["status"]["examples"]


# ═════════════════════════════════════════════════════════════════════════════
# Валидация описаний полей (DescribedFieldsGateHost)
# ═════════════════════════════════════════════════════════════════════════════


class TestDescribedFieldsValidation:
    """Обязательность описаний полей — проверяется MetadataBuilder при сборке."""

    def test_good_action_passes(self) -> None:
        """
        Действие с полностью описанными Params и Result — проходит валидацию.
        """
        # Arrange
        coordinator = GateCoordinator()

        # Act
        metadata = coordinator.get(GoodAction)

        # Assert
        assert metadata.has_params_fields()
        assert metadata.has_result_fields()

    def test_empty_models_pass(self) -> None:
        """
        Действие с пустыми Params и Result — нет полей для проверки.
        """
        # Arrange
        coordinator = GateCoordinator()

        # Act
        metadata = coordinator.get(EmptyModelsAction)

        # Assert
        assert not metadata.has_params_fields()
        assert not metadata.has_result_fields()

    def test_params_without_description_raises(self) -> None:
        """
        Поле Params без description → TypeError при сборке метаданных.
        """
        # Arrange
        coordinator = GateCoordinator()

        # Act & Assert
        with pytest.raises(TypeError, match="не имеют описания"):
            coordinator.get(BadParamsAction)

    def test_params_empty_description_raises(self) -> None:
        """
        Поле Params с пустым description → TypeError.
        """
        # Arrange
        coordinator = GateCoordinator()

        # Act & Assert
        with pytest.raises(TypeError, match="не имеют описания"):
            coordinator.get(BadParamsEmptyDescAction)

    def test_result_without_description_raises(self) -> None:
        """
        Поле Result без description → TypeError при сборке метаданных.
        """
        # Arrange
        coordinator = GateCoordinator()

        # Act & Assert
        with pytest.raises(TypeError, match="не имеют описания"):
            coordinator.get(BadResultAction)

    def test_domain_actions_pass_validation(self) -> None:
        """
        Все действия из доменной модели tests/domain/ проходят валидацию.
        """
        # Arrange
        coordinator = GateCoordinator()

        # Act & Assert — каждое действие собирается без ошибок
        for action_cls in [PingAction, SimpleAction, FullAction]:
            metadata = coordinator.get(action_cls)
            assert metadata.has_meta(), f"{action_cls.__name__} должен иметь @meta"


# ═════════════════════════════════════════════════════════════════════════════
# ClassMetadata — params_fields и result_fields
# ═════════════════════════════════════════════════════════════════════════════


class TestClassMetadataFields:
    """Тесты FieldDescriptionMeta в ClassMetadata."""

    def setup_method(self) -> None:
        """Сборка метаданных GoodAction для всех тестов класса."""
        self.coordinator = GateCoordinator()
        self.metadata = self.coordinator.get(GoodAction)

    def test_params_fields_count(self) -> None:
        """
        ClassMetadata содержит params_fields для каждого поля Params.
        OrderParams имеет 4 поля: user_id, amount, currency, comment.
        """
        # Arrange — метаданные собраны в setup_method
        # Act & Assert
        assert len(self.metadata.params_fields) == 4

    def test_result_fields_count(self) -> None:
        """
        ClassMetadata содержит result_fields для каждого поля Result.
        OrderResult имеет 3 поля: order_id, status, total.
        """
        # Arrange — метаданные собраны в setup_method
        # Act & Assert
        assert len(self.metadata.result_fields) == 3

    def test_params_field_description(self) -> None:
        """
        FieldDescriptionMeta.description содержит текст из Field(description=...).
        """
        # Arrange
        fields = {f.field_name: f for f in self.metadata.params_fields}

        # Act & Assert
        assert fields["user_id"].description == "Идентификатор пользователя"
        assert fields["amount"].description == "Сумма заказа в рублях"
        assert fields["currency"].description == "Код валюты ISO 4217"
        assert fields["comment"].description == "Комментарий к заказу"

    def test_params_field_constraints(self) -> None:
        """
        FieldDescriptionMeta.constraints содержит ограничения из Field().
        """
        # Arrange
        fields = {f.field_name: f for f in self.metadata.params_fields}

        # Act & Assert — constraints для amount
        assert "gt" in fields["amount"].constraints
        assert fields["amount"].constraints["gt"] == 0

        # Act & Assert — constraints для currency
        assert fields["currency"].constraints["min_length"] == 3
        assert fields["currency"].constraints["max_length"] == 3

    def test_params_field_examples(self) -> None:
        """
        FieldDescriptionMeta.examples содержит примеры из Field(examples=[...]).
        """
        # Arrange
        fields = {f.field_name: f for f in self.metadata.params_fields}

        # Act & Assert
        assert fields["user_id"].examples is not None
        assert "user_123" in fields["user_id"].examples

    def test_params_field_required(self) -> None:
        """
        FieldDescriptionMeta.required — True если нет default.
        """
        # Arrange
        fields = {f.field_name: f for f in self.metadata.params_fields}

        # Act & Assert
        assert fields["user_id"].required is True
        assert fields["amount"].required is True
        assert fields["currency"].required is False
        assert fields["comment"].required is False

    def test_params_field_default(self) -> None:
        """
        FieldDescriptionMeta.default содержит значение по умолчанию.
        """
        # Arrange
        fields = {f.field_name: f for f in self.metadata.params_fields}

        # Act & Assert
        assert fields["currency"].default == "RUB"
        assert fields["comment"].default is None

    def test_params_field_type_is_string(self) -> None:
        """
        FieldDescriptionMeta.field_type — строковое представление типа.
        """
        # Arrange
        fields = {f.field_name: f for f in self.metadata.params_fields}

        # Act & Assert
        assert fields["user_id"].field_type == "str"
        assert fields["amount"].field_type == "float"

    def test_result_field_constraints(self) -> None:
        """
        Constraints для Result-полей. OrderResult.total имеет ge=0.
        """
        # Arrange
        fields = {f.field_name: f for f in self.metadata.result_fields}

        # Act & Assert
        assert "ge" in fields["total"].constraints
        assert fields["total"].constraints["ge"] == 0

    def test_result_field_examples(self) -> None:
        """
        Examples для Result-полей.
        """
        # Arrange
        fields = {f.field_name: f for f in self.metadata.result_fields}

        # Act & Assert
        assert fields["status"].examples is not None
        assert "created" in fields["status"].examples


# ═════════════════════════════════════════════════════════════════════════════
# BaseState — pydantic с extra="allow", динамические поля, frozen
# ═════════════════════════════════════════════════════════════════════════════


class TestBaseStateUnchanged:
    """BaseState — pydantic с extra="allow", динамические поля, frozen."""

    def test_create_from_dict(self) -> None:
        """
        BaseState создаётся через kwargs — ключи становятся extra-полями.

        Машина создаёт BaseState через распаковку:
        BaseState(**{**old_state.to_dict(), **new_dict})
        """
        # Arrange & Act — создание через распаковку kwargs
        state = BaseState(total=1500, user="agent")

        # Assert
        assert state["total"] == 1500
        assert state["user"] == "agent"

    def test_dynamic_fields(self) -> None:
        """
        BaseState поддерживает динамическое добавление полей ТОЛЬКО через kwargs.
        После создания добавлять поля нельзя — frozen.
        """
        # Arrange — динамические поля задаются при создании через kwargs
        state = BaseState(count=42, processed=True)

        # Assert — оба поля доступны
        assert state.count == 42
        assert state.processed is True

        # Act & Assert — попытка добавить поле после создания запрещена
        with pytest.raises(ValidationError):
            state.new_field = "value"

    def test_to_dict(self) -> None:
        """
        to_dict() возвращает словарь всех extra-полей.
        """
        # Arrange
        state = BaseState(a=1, b=2)

        # Act
        d = state.to_dict()

        # Assert
        assert d == {"a": 1, "b": 2}

    def test_no_write_method(self) -> None:
        """
        Метод write() отсутствует.
        """
        # Arrange
        state = BaseState()

        # Act & Assert
        assert not hasattr(state, "write")

    def test_base_schema_interface(self) -> None:
        """
        BaseSchema: resolve, contains, keys — работают на BaseState.
        """
        # Arrange — создание через kwargs
        state = BaseState(total=1500)

        # Act & Assert
        assert state.resolve("total") == 1500
        assert state.resolve("missing", default="N/A") == "N/A"
        assert "total" in state
        assert state.keys() == ["total"]
