# tests/core/test_pydantic_integration.py
"""
Тесты интеграции pydantic BaseModel с BaseParams, BaseResult и системой метаданных.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Полное покрытие функциональности этапа 3 — перевод BaseParams и BaseResult
на pydantic BaseModel с обязательным описанием полей через Field(description="...").

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

BaseParams (pydantic, frozen=True):
    - Создание с валидными данными.
    - Frozen: попытка изменить поле → ValidationError.
    - Pydantic валидация типов: передача неверного типа → ValidationError.
    - Pydantic ограничения (gt, min_length, pattern) работают.
    - ReadableMixin: keys(), values(), items() возвращают только объявленные поля.
    - ReadableMixin: __getitem__, __contains__, get работают.
    - resolve() работает на pydantic-моделях.
    - model_json_schema() генерирует корректную JSON Schema.

BaseResult (pydantic, mutable, extra="allow"):
    - Создание и чтение полей.
    - WritableMixin: запись через __setitem__.
    - Динамические поля через extra="allow".
    - ReadableMixin: keys(), values(), items() возвращают объявленные поля.

DescribedFieldsGateHost и валидация описаний:
    - Поле без description → TypeError при сборке метаданных.
    - Поле с пустым description → TypeError.
    - Все поля с описанием → OK.
    - Пустые модели (MockParams, MockResult) → OK, без ошибок.

ClassMetadata — params_fields и result_fields:
    - ClassMetadata содержит params_fields с описаниями.
    - ClassMetadata содержит result_fields с описаниями.
    - FieldDescriptionMeta содержит constraints (gt, min_length и т.д.).
    - FieldDescriptionMeta содержит examples.
    - FieldDescriptionMeta.required корректно определяется.
    - FieldDescriptionMeta.default корректно извлекается.

BaseState — не затронут:
    - BaseState продолжает работать как dataclass с динамическими полями.
"""

import pytest
from pydantic import Field, ValidationError

from action_machine.aspects.summary_aspect import summary_aspect
from action_machine.auth.check_roles import CheckRoles
from action_machine.core.base_action import BaseAction
from action_machine.core.base_params import BaseParams
from action_machine.core.base_result import BaseResult
from action_machine.core.base_state import BaseState
from action_machine.core.gate_coordinator import GateCoordinator
from action_machine.core.meta_decorator import meta

# ═════════════════════════════════════════════════════════════════════════════
# Тестовые модели данных
# ═════════════════════════════════════════════════════════════════════════════


class OrderParams(BaseParams):
    """Параметры заказа — все поля с описанием и ограничениями."""
    user_id: str = Field(description="Идентификатор пользователя", examples=["user_123"])
    amount: float = Field(description="Сумма заказа в рублях", gt=0)
    currency: str = Field(default="RUB", description="Код валюты ISO 4217", min_length=3, max_length=3)
    comment: str | None = Field(default=None, description="Комментарий к заказу")


class OrderResult(BaseResult):
    """Результат создания заказа — все поля с описанием."""
    order_id: str = Field(description="Идентификатор созданного заказа")
    status: str = Field(description="Статус заказа", examples=["created", "pending"])
    total: float = Field(description="Итоговая сумма", ge=0)


class EmptyParams(BaseParams):
    """Пустые параметры — допустимы, валидация описаний не срабатывает."""
    pass


class EmptyResult(BaseResult):
    """Пустой результат — допустим, валидация описаний не срабатывает."""
    pass


class BadParamsNoDescription(BaseParams):
    """Параметры с полем без описания — для теста ошибки."""
    user_id: str  # нет Field(description="...")


class BadParamsEmptyDescription(BaseParams):
    """Параметры с пустым описанием — для теста ошибки."""
    user_id: str = Field(description="")


class BadResultNoDescription(BaseResult):
    """Результат с полем без описания — для теста ошибки."""
    order_id: str  # нет Field(description="...")


# ═════════════════════════════════════════════════════════════════════════════
# Тестовые действия для MetadataBuilder
# ═════════════════════════════════════════════════════════════════════════════


@meta(description="Действие с полностью описанными Params и Result")
@CheckRoles(CheckRoles.NONE, desc="Без аутентификации")
class GoodAction(BaseAction[OrderParams, OrderResult]):
    @summary_aspect("Создание заказа")
    async def summary(self, params, state, box, connections):
        return OrderResult(order_id="ORD-1", status="created", total=params.amount)


@meta(description="Действие с пустыми моделями")
@CheckRoles(CheckRoles.NONE, desc="Без аутентификации")
class EmptyModelsAction(BaseAction[EmptyParams, EmptyResult]):
    @summary_aspect("Пустой результат")
    async def summary(self, params, state, box, connections):
        return EmptyResult()


@meta(description="Действие с плохими Params")
@CheckRoles(CheckRoles.NONE, desc="")
class BadParamsAction(BaseAction[BadParamsNoDescription, OrderResult]):
    @summary_aspect("Результат")
    async def summary(self, params, state, box, connections):
        return OrderResult(order_id="ORD-1", status="ok", total=100.0)


@meta(description="Действие с пустым описанием поля Params")
@CheckRoles(CheckRoles.NONE, desc="")
class BadParamsEmptyDescAction(BaseAction[BadParamsEmptyDescription, OrderResult]):
    @summary_aspect("Результат")
    async def summary(self, params, state, box, connections):
        return OrderResult(order_id="ORD-1", status="ok", total=100.0)


@meta(description="Действие с плохим Result")
@CheckRoles(CheckRoles.NONE, desc="")
class BadResultAction(BaseAction[OrderParams, BadResultNoDescription]):
    @summary_aspect("Результат")
    async def summary(self, params, state, box, connections):
        return BadResultNoDescription(order_id="ORD-1")


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: BaseParams — pydantic поведение
# ═════════════════════════════════════════════════════════════════════════════


class TestBaseParamsPydantic:
    """Тесты pydantic-поведения BaseParams."""

    def test_create_with_valid_data(self):
        """Создание OrderParams с валидными данными."""
        params = OrderParams(user_id="user_123", amount=1500.0)
        assert params.user_id == "user_123"
        assert params.amount == 1500.0
        assert params.currency == "RUB"
        assert params.comment is None

    def test_frozen_prevents_modification(self):
        """frozen=True: попытка изменить поле → ValidationError."""
        params = OrderParams(user_id="user_123", amount=1500.0)
        with pytest.raises(ValidationError):
            params.user_id = "other_user"

    def test_type_validation_wrong_type(self):
        """Передача неверного типа → ValidationError."""
        with pytest.raises(ValidationError):
            OrderParams(user_id=123, amount="not_a_number")

    def test_constraint_gt_zero(self):
        """Ограничение gt=0: amount <= 0 → ValidationError."""
        with pytest.raises(ValidationError):
            OrderParams(user_id="user_1", amount=0)

        with pytest.raises(ValidationError):
            OrderParams(user_id="user_1", amount=-100)

    def test_constraint_min_max_length(self):
        """Ограничение min_length=3, max_length=3 для currency."""
        with pytest.raises(ValidationError):
            OrderParams(user_id="user_1", amount=100, currency="US")

        with pytest.raises(ValidationError):
            OrderParams(user_id="user_1", amount=100, currency="EURO")

    def test_default_values(self):
        """Поля с default получают значения по умолчанию."""
        params = OrderParams(user_id="u1", amount=100.0)
        assert params.currency == "RUB"
        assert params.comment is None

    def test_empty_params_valid(self):
        """Пустые BaseParams без полей — валидны."""
        params = EmptyParams()
        assert isinstance(params, BaseParams)


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: BaseParams — ReadableMixin совместимость
# ═════════════════════════════════════════════════════════════════════════════


class TestBaseParamsReadableMixin:
    """Тесты ReadableMixin на pydantic BaseParams."""

    def test_getitem(self):
        """__getitem__ возвращает значение поля."""
        params = OrderParams(user_id="u1", amount=500.0)
        assert params["user_id"] == "u1"
        assert params["amount"] == 500.0

    def test_getitem_missing_raises_key_error(self):
        """__getitem__ для несуществующего поля → KeyError."""
        params = OrderParams(user_id="u1", amount=500.0)
        with pytest.raises(KeyError):
            _ = params["nonexistent"]

    def test_contains(self):
        """__contains__ проверяет наличие поля."""
        params = OrderParams(user_id="u1", amount=500.0)
        assert "user_id" in params
        assert "amount" in params
        assert "nonexistent" not in params

    def test_get_with_default(self):
        """get() возвращает значение или default."""
        params = OrderParams(user_id="u1", amount=500.0)
        assert params.get("user_id") == "u1"
        assert params.get("nonexistent", "fallback") == "fallback"

    def test_keys_returns_model_fields_only(self):
        """keys() возвращает только объявленные поля модели."""
        params = OrderParams(user_id="u1", amount=500.0)
        keys = params.keys()
        assert "user_id" in keys
        assert "amount" in keys
        assert "currency" in keys
        assert "comment" in keys
        assert len(keys) == 4
        # Не содержит внутренних атрибутов pydantic
        assert "_resolve_cache" not in keys
        assert "__pydantic_fields_set__" not in keys

    def test_values_returns_field_values(self):
        """values() возвращает значения объявленных полей."""
        params = OrderParams(user_id="u1", amount=500.0)
        values = params.values()
        assert "u1" in values
        assert 500.0 in values
        assert "RUB" in values

    def test_items_returns_field_pairs(self):
        """items() возвращает пары (ключ, значение) для объявленных полей."""
        params = OrderParams(user_id="u1", amount=500.0)
        items = params.items()
        assert ("user_id", "u1") in items
        assert ("amount", 500.0) in items
        assert ("currency", "RUB") in items

    def test_resolve_flat_field(self):
        """resolve() работает для плоских полей pydantic-модели."""
        params = OrderParams(user_id="u1", amount=1500.0)
        assert params.resolve("user_id") == "u1"
        assert params.resolve("amount") == 1500.0
        assert params.resolve("currency") == "RUB"

    def test_resolve_missing_returns_default(self):
        """resolve() возвращает default для несуществующего пути."""
        params = OrderParams(user_id="u1", amount=500.0)
        assert params.resolve("nonexistent", default="N/A") == "N/A"

    def test_resolve_none_field(self):
        """resolve() возвращает None для поля со значением None."""
        params = OrderParams(user_id="u1", amount=500.0, comment=None)
        assert params.resolve("comment") is None


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: BaseResult — pydantic поведение
# ═════════════════════════════════════════════════════════════════════════════


class TestBaseResultPydantic:
    """Тесты pydantic-поведения BaseResult."""

    def test_create_and_read(self):
        """Создание и чтение полей Result."""
        result = OrderResult(order_id="ORD-1", status="created", total=1500.0)
        assert result.order_id == "ORD-1"
        assert result.status == "created"
        assert result.total == 1500.0

    def test_mutable_fields(self):
        """Result не frozen — поля можно изменять."""
        result = OrderResult(order_id="ORD-1", status="created", total=1500.0)
        result.status = "paid"
        assert result.status == "paid"

    def test_writable_mixin_setitem(self):
        """WritableMixin: запись через __setitem__."""
        result = OrderResult(order_id="ORD-1", status="created", total=1500.0)
        result["status"] = "shipped"
        assert result.status == "shipped"
        assert result["status"] == "shipped"

    def test_extra_fields_allowed(self):
        """extra='allow': можно записать произвольные динамические поля."""
        result = OrderResult(order_id="ORD-1", status="created", total=1500.0)
        result["debug_info"] = "extra data"
        assert result["debug_info"] == "extra data"

    def test_constraint_ge_zero(self):
        """Ограничение ge=0 на total."""
        with pytest.raises(ValidationError):
            OrderResult(order_id="ORD-1", status="fail", total=-10.0)

    def test_readable_mixin_keys(self):
        """keys() возвращает объявленные поля модели."""
        result = OrderResult(order_id="ORD-1", status="created", total=1500.0)
        keys = result.keys()
        assert "order_id" in keys
        assert "status" in keys
        assert "total" in keys

    def test_empty_result_valid(self):
        """Пустой BaseResult без полей — валиден."""
        result = EmptyResult()
        assert isinstance(result, BaseResult)


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: JSON Schema
# ═════════════════════════════════════════════════════════════════════════════


class TestJsonSchema:
    """Тесты генерации JSON Schema через pydantic."""

    def test_params_json_schema_has_descriptions(self):
        """model_json_schema() содержит описания полей."""
        schema = OrderParams.model_json_schema()
        props = schema["properties"]
        assert props["user_id"]["description"] == "Идентификатор пользователя"
        assert props["amount"]["description"] == "Сумма заказа в рублях"
        assert props["currency"]["description"] == "Код валюты ISO 4217"

    def test_params_json_schema_has_constraints(self):
        """JSON Schema содержит ограничения полей."""
        schema = OrderParams.model_json_schema()
        props = schema["properties"]
        assert props["amount"].get("exclusiveMinimum") == 0
        assert props["currency"].get("minLength") == 3
        assert props["currency"].get("maxLength") == 3

    def test_params_json_schema_has_examples(self):
        """JSON Schema содержит примеры значений."""
        schema = OrderParams.model_json_schema()
        props = schema["properties"]
        assert "examples" in props["user_id"]
        assert "user_123" in props["user_id"]["examples"]

    def test_result_json_schema_has_descriptions(self):
        """JSON Schema для Result содержит описания."""
        schema = OrderResult.model_json_schema()
        props = schema["properties"]
        assert props["order_id"]["description"] == "Идентификатор созданного заказа"
        assert props["total"]["description"] == "Итоговая сумма"

    def test_result_json_schema_has_examples(self):
        """JSON Schema для Result содержит примеры."""
        schema = OrderResult.model_json_schema()
        props = schema["properties"]
        assert "examples" in props["status"]
        assert "created" in props["status"]["examples"]

    def test_empty_params_json_schema(self):
        """JSON Schema для пустых Params корректна."""
        schema = EmptyParams.model_json_schema()
        assert "properties" in schema or schema.get("type") == "object"


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Валидация описаний полей (DescribedFieldsGateHost)
# ═════════════════════════════════════════════════════════════════════════════


class TestDescribedFieldsValidation:
    """Тесты обязательности описаний полей через MetadataBuilder."""

    def test_good_action_passes_validation(self):
        """Действие с полностью описанными Params и Result — OK."""
        coordinator = GateCoordinator()
        metadata = coordinator.get(GoodAction)
        assert metadata.has_params_fields()
        assert metadata.has_result_fields()

    def test_empty_models_pass_validation(self):
        """Действие с пустыми Params и Result — OK (нет полей для проверки)."""
        coordinator = GateCoordinator()
        metadata = coordinator.get(EmptyModelsAction)
        assert not metadata.has_params_fields()
        assert not metadata.has_result_fields()

    def test_params_without_description_raises(self):
        """Поле Params без description → TypeError при сборке метаданных."""
        coordinator = GateCoordinator()
        with pytest.raises(TypeError, match="не имеют описания"):
            coordinator.get(BadParamsAction)

    def test_params_with_empty_description_raises(self):
        """Поле Params с пустым description → TypeError."""
        coordinator = GateCoordinator()
        with pytest.raises(TypeError, match="не имеют описания"):
            coordinator.get(BadParamsEmptyDescAction)

    def test_result_without_description_raises(self):
        """Поле Result без description → TypeError при сборке метаданных."""
        coordinator = GateCoordinator()
        with pytest.raises(TypeError, match="не имеют описания"):
            coordinator.get(BadResultAction)


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: ClassMetadata — params_fields и result_fields
# ═════════════════════════════════════════════════════════════════════════════


class TestClassMetadataFields:
    """Тесты наличия и корректности params_fields и result_fields в ClassMetadata."""

    def setup_method(self):
        self.coordinator = GateCoordinator()
        self.metadata = self.coordinator.get(GoodAction)

    def test_params_fields_present(self):
        """ClassMetadata содержит params_fields."""
        assert self.metadata.has_params_fields()
        assert len(self.metadata.params_fields) == 4  # user_id, amount, currency, comment

    def test_result_fields_present(self):
        """ClassMetadata содержит result_fields."""
        assert self.metadata.has_result_fields()
        assert len(self.metadata.result_fields) == 3  # order_id, status, total

    def test_params_field_description(self):
        """FieldDescriptionMeta содержит description из Field()."""
        fields_by_name = {f.field_name: f for f in self.metadata.params_fields}
        assert fields_by_name["user_id"].description == "Идентификатор пользователя"
        assert fields_by_name["amount"].description == "Сумма заказа в рублях"
        assert fields_by_name["currency"].description == "Код валюты ISO 4217"
        assert fields_by_name["comment"].description == "Комментарий к заказу"

    def test_params_field_constraints(self):
        """FieldDescriptionMeta содержит constraints (gt, min_length и т.д.)."""
        fields_by_name = {f.field_name: f for f in self.metadata.params_fields}
        amount_constraints = fields_by_name["amount"].constraints
        assert "gt" in amount_constraints
        assert amount_constraints["gt"] == 0

        currency_constraints = fields_by_name["currency"].constraints
        assert "min_length" in currency_constraints
        assert currency_constraints["min_length"] == 3
        assert "max_length" in currency_constraints
        assert currency_constraints["max_length"] == 3

    def test_params_field_examples(self):
        """FieldDescriptionMeta содержит examples из Field()."""
        fields_by_name = {f.field_name: f for f in self.metadata.params_fields}
        assert fields_by_name["user_id"].examples is not None
        assert "user_123" in fields_by_name["user_id"].examples

    def test_params_field_required(self):
        """FieldDescriptionMeta.required корректно определяется."""
        fields_by_name = {f.field_name: f for f in self.metadata.params_fields}
        assert fields_by_name["user_id"].required is True
        assert fields_by_name["amount"].required is True
        assert fields_by_name["currency"].required is False  # есть default="RUB"
        assert fields_by_name["comment"].required is False  # есть default=None

    def test_params_field_default(self):
        """FieldDescriptionMeta.default корректно извлекается."""
        fields_by_name = {f.field_name: f for f in self.metadata.params_fields}
        assert fields_by_name["currency"].default == "RUB"
        assert fields_by_name["comment"].default is None

    def test_result_field_description(self):
        """Описания полей Result корректны."""
        fields_by_name = {f.field_name: f for f in self.metadata.result_fields}
        assert fields_by_name["order_id"].description == "Идентификатор созданного заказа"
        assert fields_by_name["status"].description == "Статус заказа"
        assert fields_by_name["total"].description == "Итоговая сумма"

    def test_result_field_constraints(self):
        """Constraints для Result полей."""
        fields_by_name = {f.field_name: f for f in self.metadata.result_fields}
        total_constraints = fields_by_name["total"].constraints
        assert "ge" in total_constraints
        assert total_constraints["ge"] == 0

    def test_result_field_examples(self):
        """Examples для Result полей."""
        fields_by_name = {f.field_name: f for f in self.metadata.result_fields}
        assert fields_by_name["status"].examples is not None
        assert "created" in fields_by_name["status"].examples

    def test_field_type_is_string(self):
        """field_type — строковое представление типа."""
        fields_by_name = {f.field_name: f for f in self.metadata.params_fields}
        assert fields_by_name["user_id"].field_type == "str"
        assert fields_by_name["amount"].field_type == "float"


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: BaseState не затронут
# ═════════════════════════════════════════════════════════════════════════════


class TestBaseStateUnchanged:
    """BaseState продолжает работать как прежде — динамические поля, не pydantic."""

    def test_create_from_dict(self):
        """BaseState создаётся из словаря."""
        state = BaseState({"total": 1500, "user": "agent"})
        assert state["total"] == 1500
        assert state["user"] == "agent"

    def test_dynamic_fields(self):
        """BaseState поддерживает динамические поля."""
        state = BaseState()
        state["count"] = 42
        state["processed"] = True
        assert state.count == 42
        assert state.processed is True

    def test_to_dict(self):
        """to_dict() возвращает все публичные атрибуты."""
        state = BaseState({"a": 1, "b": 2})
        d = state.to_dict()
        assert d == {"a": 1, "b": 2}

    def test_writable_mixin(self):
        """WritableMixin работает на BaseState."""
        state = BaseState()
        state.write("total", 1500, allowed_keys=["total", "discount"])
        assert state.total == 1500

    def test_readable_mixin(self):
        """ReadableMixin работает на BaseState."""
        state = BaseState({"total": 1500})
        assert state.resolve("total") == 1500
        assert state.resolve("missing", default="N/A") == "N/A"
        assert "total" in state
        assert state.keys() == ["total"]
