# tests2/core/test_pydantic_models.py
"""
Тесты интеграции pydantic BaseModel с BaseParams, BaseResult и метаданными.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

BaseParams и BaseResult наследуют pydantic BaseModel, что обеспечивает:

1. Валидация типов при создании экземпляра — передача str в int-поле
   вызывает ValidationError.
2. Constraints через Field(gt=0, min_length=3, pattern=...) — проверяются
   при создании и отображаются в JSON Schema.
3. Описания полей через Field(description="...") — попадают в JSON Schema,
   OpenAPI-документацию и ClassMetadata.params_fields/result_fields.
4. JSON Schema через model_json_schema() — используется FastAPI для
   автоматической генерации OpenAPI и MCP-адаптером для inputSchema.

BaseParams: frozen=True (неизменяемый после создания). ReadableMixin
обеспечивает dict-подобное чтение.

BaseResult: mutable, extra="allow" (динамические поля). ReadableMixin +
WritableMixin обеспечивают чтение и запись.

BaseState: НЕ pydantic, динамические поля. Покрыт в test_base_state.py.

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
    - ReadableMixin: keys, values, items, getitem, contains, get.
    - resolve() на pydantic-полях.

BaseResult (pydantic, mutable, extra):
    - Создание и чтение полей.
    - Mutable: изменение через setattr и __setitem__.
    - Extra-поля через extra="allow".
    - Constraints: ge и другие.
    - ReadableMixin: keys включает extra-поля.
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
from tests2.domain import FullAction, PingAction, SimpleAction

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
    async def summary(self, params, state, box, connections):
        return OrderResult(order_id="ORD-1", status="created", total=params.amount)


@meta(description="Действие с пустыми моделями")
@check_roles(ROLE_NONE)
class EmptyModelsAction(BaseAction[EmptyParams, EmptyResult]):
    """Пустые Params и Result — нет полей для проверки, проходит валидацию."""

    @summary_aspect("Пустой результат")
    async def summary(self, params, state, box, connections):
        return EmptyResult()


@meta(description="Действие с Params без description")
@check_roles(ROLE_NONE)
class BadParamsAction(BaseAction[BadParamsNoDescription, OrderResult]):
    """Поле user_id в Params без description — TypeError при сборке."""

    @summary_aspect("Результат")
    async def summary(self, params, state, box, connections):
        return OrderResult(order_id="ORD-1", status="ok", total=100.0)


@meta(description="Действие с пустым description в Params")
@check_roles(ROLE_NONE)
class BadParamsEmptyDescAction(BaseAction[BadParamsEmptyDescription, OrderResult]):
    """Пустая строка description — тоже ошибка."""

    @summary_aspect("Результат")
    async def summary(self, params, state, box, connections):
        return OrderResult(order_id="ORD-1", status="ok", total=100.0)


@meta(description="Действие с Result без description")
@check_roles(ROLE_NONE)
class BadResultAction(BaseAction[OrderParams, BadResultNoDescription]):
    """Поле order_id в Result без description — TypeError при сборке."""

    @summary_aspect("Результат")
    async def summary(self, params, state, box, connections):
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
        Если всё корректно — экземпляр создаётся без ошибок.
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

        BaseParams использует ConfigDict(frozen=True). Это делает
        экземпляр неизменяемым после создания — аспекты и плагины
        не могут случайно изменить входные параметры.
        """
        # Arrange — созданный frozen-экземпляр
        params = OrderParams(user_id="user_123", amount=1500.0)

        # Act & Assert — pydantic бросает ValidationError при попытке
        # записать значение в frozen-модель
        with pytest.raises(ValidationError):
            params.user_id = "other_user"

    def test_type_validation_rejects_wrong_type(self) -> None:
        """
        Передача неверного типа → ValidationError.

        user_id ожидает str, amount ожидает float. Передача int в user_id
        и str в amount вызывает ошибку валидации pydantic.
        """
        # Arrange & Act & Assert — неверные типы для обоих полей
        with pytest.raises(ValidationError):
            OrderParams(user_id=123, amount="not_a_number")

    def test_constraint_gt_zero(self) -> None:
        """
        Constraint gt=0: amount должен быть строго больше нуля.

        gt=0 в Field() означает exclusive minimum: 0 не допускается,
        только положительные значения.
        """
        # Arrange & Act & Assert — amount=0, нарушает gt=0
        with pytest.raises(ValidationError):
            OrderParams(user_id="u1", amount=0)

        # Arrange & Act & Assert — amount=-100, тоже нарушает gt=0
        with pytest.raises(ValidationError):
            OrderParams(user_id="u1", amount=-100)

    def test_constraint_min_max_length(self) -> None:
        """
        Constraints min_length=3, max_length=3 для currency.

        Код валюты ISO 4217 — ровно 3 символа. Меньше или больше —
        ValidationError.
        """
        # Arrange & Act & Assert — 2 символа, нарушает min_length=3
        with pytest.raises(ValidationError):
            OrderParams(user_id="u1", amount=100, currency="US")

        # Arrange & Act & Assert — 4 символа, нарушает max_length=3
        with pytest.raises(ValidationError):
            OrderParams(user_id="u1", amount=100, currency="EURO")

    def test_default_values_applied(self) -> None:
        """
        Поля с default получают значения по умолчанию при создании.

        currency="RUB" (из Field(default="RUB")), comment=None.
        """
        # Arrange & Act — создание без optional-полей
        params = OrderParams(user_id="u1", amount=100.0)

        # Assert — default-значения из Field(default=...)
        assert params.currency == "RUB"
        assert params.comment is None

    def test_empty_params_valid(self) -> None:
        """
        Пустые BaseParams без полей — валидны.

        EmptyParams() не содержит полей, pydantic создаёт пустой экземпляр.
        Это штатный сценарий для PingAction и подобных.
        """
        # Arrange & Act — создание пустых параметров
        params = EmptyParams()

        # Assert — экземпляр создан, является BaseParams
        assert isinstance(params, BaseParams)


# ═════════════════════════════════════════════════════════════════════════════
# BaseParams — ReadableMixin совместимость
# ═════════════════════════════════════════════════════════════════════════════


class TestBaseParamsReadableMixin:
    """ReadableMixin работает на pydantic BaseParams."""

    def test_getitem(self) -> None:
        """
        params["user_id"] — dict-подобный доступ через ReadableMixin.

        getattr(params, "user_id") возвращает значение pydantic-поля.
        """
        # Arrange — pydantic-модель с данными
        params = OrderParams(user_id="u1", amount=500.0)

        # Act — чтение через квадратные скобки
        # Assert — значение из pydantic-поля
        assert params["user_id"] == "u1"
        assert params["amount"] == 500.0

    def test_getitem_missing_raises_key_error(self) -> None:
        """
        params["nonexistent"] → KeyError.

        getattr бросает AttributeError, ReadableMixin оборачивает в KeyError.
        """
        # Arrange
        params = OrderParams(user_id="u1", amount=500.0)

        # Act & Assert — несуществующее поле
        with pytest.raises(KeyError):
            _ = params["nonexistent"]

    def test_contains(self) -> None:
        """
        "user_id" in params → True. "nonexistent" in params → False.
        """
        # Arrange
        params = OrderParams(user_id="u1", amount=500.0)

        # Act & Assert — hasattr проверяет наличие pydantic-атрибута
        assert "user_id" in params
        assert "amount" in params
        assert "nonexistent" not in params

    def test_get_with_default(self) -> None:
        """
        params.get("key", default) — безопасное чтение.
        """
        # Arrange
        params = OrderParams(user_id="u1", amount=500.0)

        # Act & Assert — существующий ключ
        assert params.get("user_id") == "u1"

        # Act & Assert — несуществующий ключ с default
        assert params.get("nonexistent", "fallback") == "fallback"

    def test_keys_returns_model_fields(self) -> None:
        """
        keys() возвращает только объявленные поля pydantic-модели.

        ReadableMixin._get_field_names() для pydantic использует
        type(self).model_fields.keys(). Внутренние pydantic-атрибуты
        (__pydantic_fields_set__ и т.д.) не включаются.
        """
        # Arrange
        params = OrderParams(user_id="u1", amount=500.0)

        # Act — получение ключей
        keys = params.keys()

        # Assert — четыре объявленных поля модели
        assert "user_id" in keys
        assert "amount" in keys
        assert "currency" in keys
        assert "comment" in keys
        assert len(keys) == 4

        # Assert — внутренние pydantic-атрибуты отсутствуют
        assert "_resolve_cache" not in keys

    def test_values_returns_field_values(self) -> None:
        """
        values() возвращает значения объявленных полей.
        """
        # Arrange
        params = OrderParams(user_id="u1", amount=500.0)

        # Act
        values = params.values()

        # Assert — значения всех четырёх полей
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

        # Assert — пары содержат ключи и значения
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

        # Act — resolve плоских полей
        # Assert — значения из pydantic-атрибутов
        assert params.resolve("user_id") == "u1"
        assert params.resolve("amount") == 1500.0
        assert params.resolve("currency") == "RUB"

    def test_resolve_missing_returns_default(self) -> None:
        """
        resolve("nonexistent") на pydantic-модели возвращает default.
        """
        # Arrange
        params = OrderParams(user_id="u1", amount=500.0)

        # Act & Assert — несуществующее поле → default
        assert params.resolve("nonexistent", default="N/A") == "N/A"

    def test_resolve_none_field(self) -> None:
        """
        resolve("comment") возвращает None когда поле = None.

        comment имеет default=None. resolve возвращает None,
        а не подставляет default.
        """
        # Arrange — comment не передан, default=None
        params = OrderParams(user_id="u1", amount=500.0)

        # Act — resolve поля со значением None
        result = params.resolve("comment")

        # Assert — None из атрибута, не default
        assert result is None


# ═════════════════════════════════════════════════════════════════════════════
# BaseResult — pydantic поведение
# ═════════════════════════════════════════════════════════════════════════════


class TestBaseResultPydantic:
    """Pydantic-поведение BaseResult: mutable, extra, constraints."""

    def test_create_and_read(self) -> None:
        """
        Создание OrderResult и чтение полей.
        """
        # Arrange & Act — создание результата
        result = OrderResult(order_id="ORD-1", status="created", total=1500.0)

        # Assert — все поля доступны
        assert result.order_id == "ORD-1"
        assert result.status == "created"
        assert result.total == 1500.0

    def test_mutable_fields(self) -> None:
        """
        BaseResult НЕ frozen — поля можно изменять через setattr.

        Это необходимо, потому что summary-аспект формирует результат,
        а плагины могут дополнять его (например, добавлять debug_info).
        """
        # Arrange — создание результата
        result = OrderResult(order_id="ORD-1", status="created", total=1500.0)

        # Act — изменение через setattr
        result.status = "paid"

        # Assert — значение обновлено
        assert result.status == "paid"

    def test_writable_mixin_setitem(self) -> None:
        """
        result["status"] = "shipped" — запись через WritableMixin.

        WritableMixin.__setitem__ делегирует в setattr. Для pydantic-моделей
        без frozen это эквивалентно result.status = "shipped".
        """
        # Arrange
        result = OrderResult(order_id="ORD-1", status="created", total=1500.0)

        # Act — запись через dict-подобный интерфейс
        result["status"] = "shipped"

        # Assert — значение обновлено, доступно и через точку, и через скобки
        assert result.status == "shipped"
        assert result["status"] == "shipped"

    def test_extra_fields_allowed(self) -> None:
        """
        extra="allow": запись произвольных полей, не объявленных в модели.

        BaseResult использует ConfigDict(extra="allow"). Это позволяет
        плагинам и аспектам добавлять произвольные данные в результат:
        result["debug_info"] = "extra data".
        """
        # Arrange
        result = OrderResult(order_id="ORD-1", status="created", total=1500.0)

        # Act — запись динамического поля, не объявленного в модели
        result["debug_info"] = "extra data"

        # Assert — значение сохранено и доступно
        assert result["debug_info"] == "extra data"

    def test_constraint_ge_zero(self) -> None:
        """
        Constraint ge=0 на total: допускается 0 и выше.

        ge=0 (greater than or equal) в отличие от gt=0 (strictly greater).
        """
        # Arrange & Act & Assert — total=-10 нарушает ge=0
        with pytest.raises(ValidationError):
            OrderResult(order_id="ORD-1", status="fail", total=-10.0)

    def test_keys_includes_extra_fields(self) -> None:
        """
        keys() для BaseResult с extra-полями включает и объявленные,
        и динамические поля.

        ReadableMixin._get_field_names() для pydantic с extra="allow"
        объединяет model_fields.keys() и __pydantic_extra__.keys().
        """
        # Arrange — результат с extra-полем
        result = OrderResult(order_id="ORD-1", status="created", total=1500.0)
        result["debug_info"] = "extra"

        # Act
        keys = result.keys()

        # Assert — и объявленные, и extra-поля
        assert "order_id" in keys
        assert "status" in keys
        assert "total" in keys
        assert "debug_info" in keys

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

        JSON Schema используется FastAPI для OpenAPI-документации
        и MCP-адаптером для inputSchema.
        """
        # Arrange & Act — генерация schema
        schema = OrderParams.model_json_schema()
        props = schema["properties"]

        # Assert — описания всех полей присутствуют
        assert props["user_id"]["description"] == "Идентификатор пользователя"
        assert props["amount"]["description"] == "Сумма заказа в рублях"
        assert props["currency"]["description"] == "Код валюты ISO 4217"

    def test_params_schema_has_constraints(self) -> None:
        """
        JSON Schema содержит ограничения из Field(gt=0, min_length=3 и т.д.).

        gt=0 → exclusiveMinimum=0, min_length=3 → minLength=3.
        """
        # Arrange & Act
        schema = OrderParams.model_json_schema()
        props = schema["properties"]

        # Assert — constraints преобразованы в JSON Schema формат
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

        # Assert — examples присутствуют
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

        GateCoordinator.get() вызывает MetadataBuilder.build(), который
        проверяет все поля через validate_described_fields().
        """
        # Arrange — координатор для сборки метаданных
        coordinator = GateCoordinator()

        # Act — сборка метаданных GoodAction (все поля с description)
        metadata = coordinator.get(GoodAction)

        # Assert — params_fields и result_fields собраны
        assert metadata.has_params_fields()
        assert metadata.has_result_fields()

    def test_empty_models_pass(self) -> None:
        """
        Действие с пустыми Params и Result — нет полей для проверки.

        EmptyParams и EmptyResult не содержат полей. Валидатор
        пропускает пустые модели — нечего проверять.
        """
        # Arrange
        coordinator = GateCoordinator()

        # Act — сборка метаданных EmptyModelsAction
        metadata = coordinator.get(EmptyModelsAction)

        # Assert — нет полей
        assert not metadata.has_params_fields()
        assert not metadata.has_result_fields()

    def test_params_without_description_raises(self) -> None:
        """
        Поле Params без description → TypeError при сборке метаданных.

        BadParamsNoDescription содержит user_id: str без Field(description=...).
        MetadataBuilder.build() → validate_described_fields() → TypeError.
        """
        # Arrange
        coordinator = GateCoordinator()

        # Act & Assert — сборка бросает TypeError с указанием поля
        with pytest.raises(TypeError, match="не имеют описания"):
            coordinator.get(BadParamsAction)

    def test_params_empty_description_raises(self) -> None:
        """
        Поле Params с пустым description → TypeError.

        Field(description="") — пустая строка, считается отсутствием описания.
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
        Все действия из доменной модели tests2/domain/ проходят валидацию.

        PingAction, SimpleAction, FullAction — все поля имеют description.
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

        # Act & Assert — четыре FieldDescriptionMeta
        assert len(self.metadata.params_fields) == 4

    def test_result_fields_count(self) -> None:
        """
        ClassMetadata содержит result_fields для каждого поля Result.

        OrderResult имеет 3 поля: order_id, status, total.
        """
        # Arrange — метаданные собраны в setup_method

        # Act & Assert — три FieldDescriptionMeta
        assert len(self.metadata.result_fields) == 3

    def test_params_field_description(self) -> None:
        """
        FieldDescriptionMeta.description содержит текст из Field(description=...).
        """
        # Arrange — словарь полей по имени
        fields = {f.field_name: f for f in self.metadata.params_fields}

        # Act & Assert — описания всех четырёх полей
        assert fields["user_id"].description == "Идентификатор пользователя"
        assert fields["amount"].description == "Сумма заказа в рублях"
        assert fields["currency"].description == "Код валюты ISO 4217"
        assert fields["comment"].description == "Комментарий к заказу"

    def test_params_field_constraints(self) -> None:
        """
        FieldDescriptionMeta.constraints содержит ограничения из Field().

        Constraints извлекаются из FieldInfo.metadata — списка
        pydantic annotated-объектов (Gt, MinLen и т.д.).
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

        # Act & Assert — examples для user_id
        assert fields["user_id"].examples is not None
        assert "user_123" in fields["user_id"].examples

    def test_params_field_required(self) -> None:
        """
        FieldDescriptionMeta.required — True если нет default.

        user_id и amount — обязательные (нет default).
        currency и comment — необязательные (есть default).
        """
        # Arrange
        fields = {f.field_name: f for f in self.metadata.params_fields}

        # Act & Assert — обязательные и необязательные поля
        assert fields["user_id"].required is True
        assert fields["amount"].required is True
        assert fields["currency"].required is False
        assert fields["comment"].required is False

    def test_params_field_default(self) -> None:
        """
        FieldDescriptionMeta.default содержит значение по умолчанию.

        currency default="RUB", comment default=None.
        """
        # Arrange
        fields = {f.field_name: f for f in self.metadata.params_fields}

        # Act & Assert — default-значения
        assert fields["currency"].default == "RUB"
        assert fields["comment"].default is None

    def test_params_field_type_is_string(self) -> None:
        """
        FieldDescriptionMeta.field_type — строковое представление типа.

        Аннотации типов могут содержать Union, Optional и другие формы,
        не являющиеся type. Поэтому field_type — строка, а не type.
        """
        # Arrange
        fields = {f.field_name: f for f in self.metadata.params_fields}

        # Act & Assert — строковые представления типов
        assert fields["user_id"].field_type == "str"
        assert fields["amount"].field_type == "float"

    def test_result_field_constraints(self) -> None:
        """
        Constraints для Result-полей.

        OrderResult.total имеет ge=0.
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
# BaseState не затронут pydantic-миграцией
# ═════════════════════════════════════════════════════════════════════════════


class TestBaseStateUnchanged:
    """BaseState — не pydantic, динамические поля, работает как прежде."""

    def test_create_from_dict(self) -> None:
        """
        BaseState создаётся из словаря — ключи становятся атрибутами.
        Это НЕ pydantic: нет валидации типов, нет frozen, нет model_fields.
        """
        # Arrange & Act
        state = BaseState({"total": 1500, "user": "agent"})

        # Assert
        assert state["total"] == 1500
        assert state["user"] == "agent"

    def test_dynamic_fields(self) -> None:
        """
        BaseState поддерживает динамическое добавление полей.
        """
        # Arrange
        state = BaseState()

        # Act — динамическая запись
        state["count"] = 42
        state["processed"] = True

        # Assert — оба поля доступны
        assert state.count == 42
        assert state.processed is True

    def test_to_dict(self) -> None:
        """
        to_dict() возвращает словарь публичных атрибутов.
        """
        # Arrange
        state = BaseState({"a": 1, "b": 2})

        # Act
        d = state.to_dict()

        # Assert
        assert d == {"a": 1, "b": 2}

    def test_writable_mixin(self) -> None:
        """
        WritableMixin.write() работает на BaseState.
        """
        # Arrange
        state = BaseState()

        # Act
        state.write("total", 1500, allowed_keys=["total", "discount"])

        # Assert
        assert state.total == 1500

    def test_readable_mixin(self) -> None:
        """
        ReadableMixin: resolve, contains, keys — работают на BaseState.
        """
        # Arrange
        state = BaseState({"total": 1500})

        # Act & Assert
        assert state.resolve("total") == 1500
        assert state.resolve("missing", default="N/A") == "N/A"
        assert "total" in state
        assert state.keys() == ["total"]
