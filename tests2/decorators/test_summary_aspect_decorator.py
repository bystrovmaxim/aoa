# tests2/decorators/test_summary_aspect_decorator.py
"""
Тесты декоратора @summary_aspect — объявление завершающего шага действия.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Декоратор @summary_aspect помечает async-метод как финальный шаг конвейера,
который формирует Result действия. В каждом действии допускается ровно один
summary_aspect. Он выполняется после всех regular_aspect, получает
накопленный state и возвращает типизированный Result.

Декоратор при применении:
1. Проверяет, что description — строка.
2. Проверяет, что цель — callable.
3. Проверяет, что метод — async def.
4. Проверяет, что число параметров == 5 (self, params, state, box, connections).
5. Записывает _new_aspect_meta = {"type": "summary", "description": ...}.

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

Валидное применение:
    - Async-метод с 5 параметрами — записывает _new_aspect_meta.
    - type="summary" в meta.
    - С описанием и без описания.

Невалидные аргументы:
    - description не строка → TypeError.

Невалидные цели:
    - Не callable → TypeError.
    - Синхронный метод → TypeError.
    - Неверное число параметров → TypeError.

Структурные инварианты (через MetadataBuilder):
    - Не более одного summary-аспекта на класс.
    - Regular без summary — ошибка.
    - Summary должен быть объявлен последним.
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
    """Декоратор корректно записывает _new_aspect_meta с type="summary"."""

    def test_writes_aspect_meta(self) -> None:
        """
        @summary_aspect("Описание") записывает _new_aspect_meta в метод.

        _new_aspect_meta = {"type": "summary", "description": "Описание"}.
        """
        # Arrange & Act
        @summary_aspect("Формирование результата")
        async def build_result(self, params, state, box, connections):
            return BaseResult()

        # Assert
        assert hasattr(build_result, "_new_aspect_meta")
        assert build_result._new_aspect_meta["type"] == "summary"
        assert build_result._new_aspect_meta["description"] == "Формирование результата"

    def test_type_is_summary(self) -> None:
        """
        type в _new_aspect_meta всегда "summary" для @summary_aspect.

        Отличает от @regular_aspect, где type="regular".
        """
        # Arrange & Act
        @summary_aspect("итог")
        async def finish(self, params, state, box, connections):
            return BaseResult()

        # Assert
        assert finish._new_aspect_meta["type"] == "summary"

    def test_empty_description(self) -> None:
        """
        @summary_aspect() без описания — пустая строка по умолчанию.
        """
        # Arrange & Act
        @summary_aspect()
        async def finish(self, params, state, box, connections):
            return BaseResult()

        # Assert
        assert finish._new_aspect_meta["description"] == ""

    def test_returns_function_unchanged(self) -> None:
        """
        Декоратор возвращает ту же функцию — не оборачивает.
        """
        # Arrange
        async def original(self, params, state, box, connections):
            return BaseResult()

        # Act
        decorated = summary_aspect("test")(original)

        # Assert — тот же объект
        assert decorated is original


# ═════════════════════════════════════════════════════════════════════════════
# Невалидные аргументы
# ═════════════════════════════════════════════════════════════════════════════


class TestInvalidArgs:
    """Невалидные аргументы → TypeError."""

    def test_description_not_string_raises(self) -> None:
        """
        @summary_aspect(42) → TypeError.
        """
        # Arrange & Act & Assert
        with pytest.raises(TypeError, match="строку description"):
            summary_aspect(42)

    def test_description_none_raises(self) -> None:
        """
        @summary_aspect(None) → TypeError.
        """
        # Arrange & Act & Assert
        with pytest.raises(TypeError, match="строку description"):
            summary_aspect(None)


# ═════════════════════════════════════════════════════════════════════════════
# Невалидные цели
# ═════════════════════════════════════════════════════════════════════════════


class TestInvalidTarget:
    """Декоратор применён к невалидной цели → TypeError."""

    def test_not_callable_raises(self) -> None:
        """
        @summary_aspect("test") на строке → TypeError.
        """
        # Arrange & Act & Assert
        with pytest.raises(TypeError, match="только к методам"):
            summary_aspect("test")("not_a_function")

    def test_sync_function_raises(self) -> None:
        """
        @summary_aspect("test") на синхронной функции → TypeError.
        """
        # Arrange & Act & Assert
        with pytest.raises(TypeError, match="асинхронным"):
            @summary_aspect("test")
            def sync_method(self, params, state, box, connections):
                return BaseResult()

    def test_wrong_param_count_raises(self) -> None:
        """
        @summary_aspect("test") на методе с 3 параметрами → TypeError.

        Ожидается ровно 5: self, params, state, box, connections.
        """
        # Arrange & Act & Assert
        with pytest.raises(TypeError, match="5 параметров"):
            @summary_aspect("test")
            async def bad_method(self, params, state):
                return BaseResult()

    def test_too_many_params_raises(self) -> None:
        """
        @summary_aspect("test") на методе с 6 параметрами → TypeError.
        """
        # Arrange & Act & Assert
        with pytest.raises(TypeError, match="5 параметров"):
            @summary_aspect("test")
            async def bad_method(self, params, state, box, connections, extra):
                return BaseResult()

    def test_no_params_raises(self) -> None:
        """
        @summary_aspect("test") на методе без параметров → TypeError.
        """
        # Arrange & Act & Assert
        with pytest.raises(TypeError, match="5 параметров"):
            @summary_aspect("test")
            async def bad_method():
                return BaseResult()


# ═════════════════════════════════════════════════════════════════════════════
# Структурные инварианты (через MetadataBuilder)
# ═════════════════════════════════════════════════════════════════════════════


class TestStructuralInvariants:
    """MetadataBuilder проверяет структурные инварианты аспектов."""

    def test_two_summary_aspects_raises(self) -> None:
        """
        Два @summary_aspect на одном классе → ValueError при сборке.

        Допускается не более одного summary-аспекта.
        """
        # Arrange
        @meta(description="Тест")
        @check_roles(ROLE_NONE)
        class _Action(BaseAction[BaseParams, BaseResult]):
            @summary_aspect("Первый")
            async def summary_one(self, params, state, box, connections):
                return BaseResult()

            @summary_aspect("Второй")
            async def summary_two(self, params, state, box, connections):
                return BaseResult()

        coordinator = GateCoordinator()

        # Act & Assert — ValueError при сборке
        with pytest.raises(ValueError, match="summary"):
            coordinator.get(_Action)

    def test_regular_without_summary_raises(self) -> None:
        """
        Regular-аспект без summary → ValueError при сборке.

        Действие должно завершаться summary-аспектом.
        """
        # Arrange
        @meta(description="Тест")
        @check_roles(ROLE_NONE)
        class _Action(BaseAction[BaseParams, BaseResult]):
            @regular_aspect("Шаг")
            async def step(self, params, state, box, connections):
                return {}

        coordinator = GateCoordinator()

        # Act & Assert — ValueError
        with pytest.raises(ValueError, match="summary"):
            coordinator.get(_Action)

    def test_summary_not_last_raises(self) -> None:
        """
        Summary объявлен перед regular → ValueError при сборке.

        Summary должен быть последним среди аспектов.
        """
        # Arrange
        @meta(description="Тест")
        @check_roles(ROLE_NONE)
        class _Action(BaseAction[BaseParams, BaseResult]):
            @summary_aspect("Итог")
            async def summary(self, params, state, box, connections):
                return BaseResult()

            @regular_aspect("Шаг после summary")
            async def step_after(self, params, state, box, connections):
                return {}

        coordinator = GateCoordinator()

        # Act & Assert — ValueError
        with pytest.raises(ValueError, match="последним"):
            coordinator.get(_Action)

    def test_only_summary_is_valid(self) -> None:
        """
        Действие только с summary (без regular) — валидно.

        PingAction — пример такого действия: один summary-аспект,
        ноль regular-аспектов.
        """
        # Arrange
        @meta(description="Минимальное действие")
        @check_roles(ROLE_NONE)
        class _Action(BaseAction[BaseParams, BaseResult]):
            @summary_aspect("Pong")
            async def summary(self, params, state, box, connections):
                return BaseResult()

        coordinator = GateCoordinator()

        # Act — сборка без ошибок
        metadata = coordinator.get(_Action)

        # Assert — один summary, ноль regular
        assert metadata.get_summary_aspect() is not None
        assert len(metadata.get_regular_aspects()) == 0


# ═════════════════════════════════════════════════════════════════════════════
# Интеграция с MetadataBuilder
# ═════════════════════════════════════════════════════════════════════════════


class TestMetadataIntegration:
    """MetadataBuilder собирает AspectMeta с type="summary"."""

    def test_summary_in_metadata(self) -> None:
        """
        get_summary_aspect() возвращает AspectMeta с type="summary".
        """
        # Arrange
        @meta(description="Тест")
        @check_roles(ROLE_NONE)
        class _Action(BaseAction[BaseParams, BaseResult]):
            @summary_aspect("Формирование ответа")
            async def build(self, params, state, box, connections):
                return BaseResult()

        coordinator = GateCoordinator()

        # Act
        metadata = coordinator.get(_Action)
        summary = metadata.get_summary_aspect()

        # Assert
        assert summary is not None
        assert summary.aspect_type == "summary"
        assert summary.description == "Формирование ответа"
        assert summary.method_name == "build"
        assert callable(summary.method_ref)
