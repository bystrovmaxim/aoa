# tests/decorators/test_aspect_checks.py
"""
Тесты проверок декораторов @regular_aspect и @summary_aspect.

Покрывают все инварианты, объявленные в regular_aspect.py и summary_aspect.py:
    - Применение к async-методу с 5 параметрами — успех.
    - Применение к синхронному методу — TypeError.
    - Применение к методу с неверным числом параметров — TypeError.
    - Применение к не-callable объекту — TypeError.
    - Нестроковый description — TypeError.
    - Проверка метаданных _new_aspect_meta после декорирования.
    - staticmethod/classmethod — проверяется отдельно (в тестах хоста),
      так как на этапе декорирования Python ещё не обернул метод.
"""

import pytest

from action_machine.aspects.regular_aspect import regular_aspect
from action_machine.aspects.summary_aspect import summary_aspect

# ─────────────────────────────────────────────────────────────────────────────
# Вспомогательные функции для тестов
# ─────────────────────────────────────────────────────────────────────────────

async def _valid_aspect_method(self, params, state, box, connections):
    """Заглушка с правильной сигнатурой для тестов."""
    return {}


async def _too_few_params(self, params, state):
    """Заглушка с недостаточным числом параметров."""
    return {}


async def _too_many_params(self, params, state, box, connections, extra):
    """Заглушка с избыточным числом параметров."""
    return {}


def _sync_method(self, params, state, box, connections):
    """Синхронная заглушка — не async def."""
    return {}


# ─────────────────────────────────────────────────────────────────────────────
# @regular_aspect: успешные сценарии
# ─────────────────────────────────────────────────────────────────────────────

class TestRegularAspectSuccess:
    """Проверка корректного применения @regular_aspect."""

    def test_valid_async_method(self):
        """async-метод с 5 параметрами — декоратор прикрепляет метаданные."""

        @regular_aspect("Тестовый шаг")
        async def process(self, params, state, box, connections):
            return {}

        assert hasattr(process, '_new_aspect_meta')
        assert process._new_aspect_meta["type"] == "regular"
        assert process._new_aspect_meta["description"] == "Тестовый шаг"

    def test_default_description(self):
        """Description по умолчанию — пустая строка."""

        @regular_aspect()
        async def process(self, params, state, box, connections):
            return {}

        assert process._new_aspect_meta["description"] == ""

    def test_does_not_change_function_name(self):
        """Декоратор не меняет имя функции."""

        @regular_aspect("Шаг")
        async def my_step(self, params, state, box, connections):
            return {}

        assert my_step.__name__ == "my_step"

    def test_function_remains_callable(self):
        """Декорированная функция остаётся вызываемой."""

        @regular_aspect("Шаг")
        async def my_step(self, params, state, box, connections):
            return {}

        assert callable(my_step)


# ─────────────────────────────────────────────────────────────────────────────
# @regular_aspect: ошибки
# ─────────────────────────────────────────────────────────────────────────────

class TestRegularAspectErrors:
    """Проверка ошибок @regular_aspect при нарушении инвариантов."""

    def test_sync_method_raises(self):
        """Синхронный метод — TypeError."""
        with pytest.raises(TypeError, match="должен быть асинхронным"):
            @regular_aspect("Шаг")
            def process(self, params, state, box, connections):
                return {}

    def test_too_few_params_raises(self):
        """Менее 5 параметров — TypeError."""
        with pytest.raises(TypeError, match="должен принимать 5 параметров"):
            @regular_aspect("Шаг")
            async def process(self, params, state):
                return {}

    def test_too_many_params_raises(self):
        """Более 5 параметров — TypeError."""
        with pytest.raises(TypeError, match="должен принимать 5 параметров"):
            @regular_aspect("Шаг")
            async def process(self, params, state, box, connections, extra):
                return {}

    def test_not_callable_raises(self):
        """Не-callable объект — TypeError."""
        with pytest.raises(TypeError, match="только к методам"):
            regular_aspect("Шаг")("not a function")

    def test_invalid_description_raises(self):
        """Нестроковый description — TypeError."""
        with pytest.raises(TypeError, match="ожидает строку description"):
            regular_aspect(123)

    def test_none_description_raises(self):
        """None вместо description — TypeError."""
        with pytest.raises(TypeError, match="ожидает строку description"):
            regular_aspect(None)


# ─────────────────────────────────────────────────────────────────────────────
# @summary_aspect: успешные сценарии
# ─────────────────────────────────────────────────────────────────────────────

class TestSummaryAspectSuccess:
    """Проверка корректного применения @summary_aspect."""

    def test_valid_async_method(self):
        """async-метод с 5 параметрами — декоратор прикрепляет метаданные."""

        @summary_aspect("Формирование результата")
        async def build_result(self, params, state, box, connections):
            return {}

        assert hasattr(build_result, '_new_aspect_meta')
        assert build_result._new_aspect_meta["type"] == "summary"
        assert build_result._new_aspect_meta["description"] == "Формирование результата"

    def test_default_description(self):
        """Description по умолчанию — пустая строка."""

        @summary_aspect()
        async def build_result(self, params, state, box, connections):
            return {}

        assert build_result._new_aspect_meta["description"] == ""

    def test_does_not_change_function_name(self):
        """Декоратор не меняет имя функции."""

        @summary_aspect("Результат")
        async def my_result(self, params, state, box, connections):
            return {}

        assert my_result.__name__ == "my_result"


# ─────────────────────────────────────────────────────────────────────────────
# @summary_aspect: ошибки
# ─────────────────────────────────────────────────────────────────────────────

class TestSummaryAspectErrors:
    """Проверка ошибок @summary_aspect при нарушении инвариантов."""

    def test_sync_method_raises(self):
        """Синхронный метод — TypeError."""
        with pytest.raises(TypeError, match="должен быть асинхронным"):
            @summary_aspect("Результат")
            def build_result(self, params, state, box, connections):
                return {}

    def test_too_few_params_raises(self):
        """Менее 5 параметров — TypeError."""
        with pytest.raises(TypeError, match="должен принимать 5 параметров"):
            @summary_aspect("Результат")
            async def build_result(self, params):
                return {}

    def test_too_many_params_raises(self):
        """Более 5 параметров — TypeError."""
        with pytest.raises(TypeError, match="должен принимать 5 параметров"):
            @summary_aspect("Результат")
            async def build_result(self, params, state, box, connections, extra):
                return {}

    def test_not_callable_raises(self):
        """Не-callable объект — TypeError."""
        with pytest.raises(TypeError, match="только к методам"):
            summary_aspect("Результат")(42)

    def test_invalid_description_raises(self):
        """Нестроковый description — TypeError."""
        with pytest.raises(TypeError, match="ожидает строку description"):
            summary_aspect(123)

    def test_string_raises(self):
        """Строка вместо функции — TypeError (не callable)."""
        with pytest.raises(TypeError, match="только к методам"):
            summary_aspect("Результат")("not a function")
