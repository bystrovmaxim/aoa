# tests/decorators/test_regular_aspect_decorator.py
"""
Тесты декоратора @regular_aspect — объявление шага конвейера бизнес-логики.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Декоратор @regular_aspect помечает async-метод действия как регулярный
аспект — один шаг в линейном конвейере обработки. Машина выполняет
регулярные аспекты последовательно, в порядке их объявления в классе.

Декоратор при применении:
1. Проверяет, что description — непустая строка.
2. Проверяет, что цель — callable.
3. Проверяет, что метод — async def.
4. Проверяет, что число параметров == 5 (self, params, state, box, connections).
5. Проверяет, что имя метода заканчивается на _aspect.
6. Записывает _new_aspect_meta = {"type": "regular", "description": ...}.

MetadataBuilder._collect_aspects(cls) находит методы с _new_aspect_meta
и включает их в ClassMetadata.aspects.

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

Валидное применение:
    - Async-метод с 5 параметрами и суффиксом _aspect — записывает _new_aspect_meta.
    - С описанием — description сохраняется в meta.
    - Метод возвращается без изменений.

Невалидные аргументы:
    - description не строка → TypeError.
    - description пустая строка → ValueError.
    - description не передан → TypeError.

Невалидные цели:
    - Не callable → TypeError.
    - Синхронный метод (не async) → TypeError.
    - Неверное число параметров (не 5) → TypeError.

Интеграция:
    - MetadataBuilder собирает AspectMeta с type="regular".
    - Порядок аспектов соответствует порядку объявления.
"""

import pytest

from action_machine.aspects.regular_aspect import regular_aspect
from action_machine.aspects.summary_aspect import summary_aspect
from action_machine.auth import ROLE_NONE, check_roles
from action_machine.core.base_action import BaseAction
from action_machine.core.base_params import BaseParams
from action_machine.core.base_result import BaseResult
from action_machine.core.gate_coordinator import GateCoordinator
from action_machine.core.meta_decorator import meta

# ═════════════════════════════════════════════════════════════════════════════
# Валидное применение
# ═════════════════════════════════════════════════════════════════════════════


class TestValidUsage:
    """Декоратор корректно записывает _new_aspect_meta на async-метод."""

    def test_writes_aspect_meta(self) -> None:
        """
        @regular_aspect("Описание") записывает _new_aspect_meta в метод.

        _new_aspect_meta = {"type": "regular", "description": "Описание"}.
        """
        # Arrange & Act — декоратор на async-методе с 5 параметрами
        @regular_aspect("Валидация данных")
        async def validate_aspect(self, params, state, box, connections):
            return {}

        # Assert — _new_aspect_meta записан
        assert hasattr(validate_aspect, "_new_aspect_meta")
        assert validate_aspect._new_aspect_meta["type"] == "regular"
        assert validate_aspect._new_aspect_meta["description"] == "Валидация данных"

    def test_description_is_required(self) -> None:
        """
        @regular_aspect() без аргументов → TypeError.

        description — обязательный позиционный аргумент.
        """
        # Arrange & Act & Assert
        with pytest.raises(TypeError):
            regular_aspect()

    def test_empty_description_raises(self) -> None:
        """
        @regular_aspect("") — пустая строка → ValueError.

        description не может быть пустой строкой.
        """
        # Arrange & Act & Assert
        with pytest.raises(ValueError, match="пустой"):
            @regular_aspect("")
            async def step_aspect(self, params, state, box, connections):
                return {}

    def test_returns_function_unchanged(self) -> None:
        """
        Декоратор возвращает ту же функцию — не оборачивает.

        @regular_aspect только добавляет атрибут _new_aspect_meta,
        не создаёт wrapper-функцию.
        """
        # Arrange
        async def original_aspect(self, params, state, box, connections):
            return {}

        # Act
        decorated = regular_aspect("test")(original_aspect)

        # Assert — тот же объект
        assert decorated is original_aspect

    def test_type_is_regular(self) -> None:
        """
        type в _new_aspect_meta всегда "regular" для @regular_aspect.

        Отличает от @summary_aspect, где type="summary".
        """
        # Arrange & Act
        @regular_aspect("шаг")
        async def step_aspect(self, params, state, box, connections):
            return {}

        # Assert
        assert step_aspect._new_aspect_meta["type"] == "regular"


# ═════════════════════════════════════════════════════════════════════════════
# Невалидные аргументы
# ═════════════════════════════════════════════════════════════════════════════


class TestInvalidArgs:
    """Невалидные аргументы → TypeError."""

    def test_description_not_string_raises(self) -> None:
        """
        @regular_aspect(42) → TypeError.

        description должен быть строкой.
        """
        # Arrange & Act & Assert
        with pytest.raises(TypeError, match="строку description"):
            regular_aspect(42)

    def test_description_none_raises(self) -> None:
        """
        @regular_aspect(None) → TypeError.
        """
        # Arrange & Act & Assert
        with pytest.raises(TypeError, match="строку description"):
            regular_aspect(None)

    def test_description_list_raises(self) -> None:
        """
        @regular_aspect(["a", "b"]) → TypeError.
        """
        # Arrange & Act & Assert
        with pytest.raises(TypeError, match="строку description"):
            regular_aspect(["a", "b"])


# ═════════════════════════════════════════════════════════════════════════════
# Невалидные цели
# ═════════════════════════════════════════════════════════════════════════════


class TestInvalidTarget:
    """Декоратор применён к невалидной цели → TypeError."""

    def test_not_callable_raises(self) -> None:
        """
        @regular_aspect("test") на строке → TypeError.

        Цель должна быть callable (функция, метод).
        """
        # Arrange & Act & Assert
        with pytest.raises(TypeError, match="только к методам"):
            regular_aspect("test")("not_a_function")

    def test_sync_function_raises(self) -> None:
        """
        @regular_aspect("test") на синхронной функции → TypeError.

        Все аспекты обязаны быть async def.
        """
        # Arrange & Act & Assert
        with pytest.raises(TypeError, match="асинхронным"):
            @regular_aspect("test")
            def sync_method_aspect(self, params, state, box, connections):
                return {}

    def test_wrong_param_count_raises(self) -> None:
        """
        @regular_aspect("test") на методе с 3 параметрами → TypeError.

        Ожидается ровно 5: self, params, state, box, connections.
        """
        # Arrange & Act & Assert
        with pytest.raises(TypeError, match="5 параметров"):
            @regular_aspect("test")
            async def bad_method_aspect(self, params, state):
                return {}

    def test_too_many_params_raises(self) -> None:
        """
        @regular_aspect("test") на методе с 6 параметрами → TypeError.
        """
        # Arrange & Act & Assert
        with pytest.raises(TypeError, match="5 параметров"):
            @regular_aspect("test")
            async def bad_method_aspect(self, params, state, box, connections, extra):
                return {}

    def test_no_params_raises(self) -> None:
        """
        @regular_aspect("test") на методе без параметров → TypeError.
        """
        # Arrange & Act & Assert
        with pytest.raises(TypeError, match="5 параметров"):
            @regular_aspect("test")
            async def bad_method_aspect():
                return {}


# ═════════════════════════════════════════════════════════════════════════════
# Интеграция с MetadataBuilder
# ═════════════════════════════════════════════════════════════════════════════


class TestMetadataIntegration:
    """MetadataBuilder собирает AspectMeta из _new_aspect_meta."""

    def test_single_regular_aspect_in_metadata(self) -> None:
        """
        Один @regular_aspect → один AspectMeta с type="regular" в metadata.
        """
        # Arrange
        @meta(description="Тест")
        @check_roles(ROLE_NONE)
        class _ValidateAction(BaseAction[BaseParams, BaseResult]):
            @regular_aspect("Валидация")
            async def validate_aspect(self, params, state, box, connections):
                return {}

            @summary_aspect("Результат")
            async def build_summary(self, params, state, box, connections):
                return BaseResult()

        coordinator = GateCoordinator()

        # Act
        metadata = coordinator.get(_ValidateAction)
        regulars = metadata.get_regular_aspects()

        # Assert — один regular-аспект
        assert len(regulars) == 1
        assert regulars[0].method_name == "validate_aspect"
        assert regulars[0].aspect_type == "regular"
        assert regulars[0].description == "Валидация"

    def test_aspect_order_preserved(self) -> None:
        """
        Порядок аспектов в metadata соответствует порядку объявления в классе.

        Машина выполняет regular-аспекты последовательно в этом порядке.
        """
        # Arrange
        @meta(description="Тест")
        @check_roles(ROLE_NONE)
        class _TwoStepAction(BaseAction[BaseParams, BaseResult]):
            @regular_aspect("Первый")
            async def step_one_aspect(self, params, state, box, connections):
                return {}

            @regular_aspect("Второй")
            async def step_two_aspect(self, params, state, box, connections):
                return {}

            @summary_aspect("Итог")
            async def build_summary(self, params, state, box, connections):
                return BaseResult()

        coordinator = GateCoordinator()

        # Act
        metadata = coordinator.get(_TwoStepAction)
        regulars = metadata.get_regular_aspects()

        # Assert — порядок сохранён
        assert len(regulars) == 2
        assert regulars[0].method_name == "step_one_aspect"
        assert regulars[1].method_name == "step_two_aspect"

    def test_method_ref_is_callable(self) -> None:
        """
        AspectMeta.method_ref — ссылка на оригинальную функцию.

        Машина вызывает method_ref(action, params, state, box, connections)
        при выполнении аспекта.
        """
        # Arrange
        @meta(description="Тест")
        @check_roles(ROLE_NONE)
        class _StepAction(BaseAction[BaseParams, BaseResult]):
            @regular_aspect("Шаг")
            async def step_aspect(self, params, state, box, connections):
                return {}

            @summary_aspect("Итог")
            async def build_summary(self, params, state, box, connections):
                return BaseResult()

        coordinator = GateCoordinator()

        # Act
        metadata = coordinator.get(_StepAction)
        regulars = metadata.get_regular_aspects()

        # Assert — method_ref callable
        assert callable(regulars[0].method_ref)
