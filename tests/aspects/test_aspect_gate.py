# tests/aspects/test_aspect_gate.py
"""
Тесты для AspectGate — шлюза управления аспектами действия.

Проверяем:
- Регистрацию обычных аспектов (regular)
- Регистрацию summary-аспекта (только один)
- Повторную регистрацию summary-аспекта (вызывает ValueError)
- Получение обычных аспектов (get_regular) и summary (get_summary)
- Удаление аспектов (unregister)
- Сохранение порядка регистрации
- Возврат копий списков

Изменения:
- Исправлен тест `test_register_without_description_raises`: теперь ожидается ValueError,
  так как в AspectGate.register при отсутствии описания выбрасывается ValueError,
  а не KeyError.
"""

import pytest

from action_machine.aspects.aspect_gate import AspectGate


class DummyAspect:
    """Фиктивный аспект для тестов."""

    __name__ = "dummy"
    __qualname__ = "DummyAspect"

    async def __call__(self, *args, **kwargs):
        pass


class TestAspectGate:
    """Тесты для AspectGate."""

    # ------------------------------------------------------------------
    # Регистрация обычных аспектов
    # ------------------------------------------------------------------
    def test_register_regular(self):
        """Регистрация обычного аспекта."""
        gate = AspectGate()
        method = DummyAspect()
        gate.register(method, description="test description", type="regular")

        assert gate.get_regular() == [(method, "test description")]
        assert gate.get_summary() is None

    def test_register_multiple_regular(self):
        """Регистрация нескольких обычных аспектов (порядок сохраняется)."""
        gate = AspectGate()
        m1 = DummyAspect()
        m2 = DummyAspect()

        gate.register(m1, description="first", type="regular")
        gate.register(m2, description="second", type="regular")

        regular = gate.get_regular()
        assert len(regular) == 2
        assert regular[0] == (m1, "first")
        assert regular[1] == (m2, "second")

    # ------------------------------------------------------------------
    # Регистрация summary-аспекта
    # ------------------------------------------------------------------
    def test_register_summary(self):
        """Регистрация summary-аспекта."""
        gate = AspectGate()
        method = DummyAspect()
        gate.register(method, description="summary description", type="summary")

        assert gate.get_regular() == []
        assert gate.get_summary() == (method, "summary description")

    def test_register_two_summaries_raises(self):
        """Повторная регистрация summary-аспекта вызывает ValueError."""
        gate = AspectGate()
        m1 = DummyAspect()
        m2 = DummyAspect()

        gate.register(m1, description="first", type="summary")
        with pytest.raises(ValueError, match="Разрешён только один summary-аспект"):
            gate.register(m2, description="second", type="summary")

    # ------------------------------------------------------------------
    # Обработка ошибок
    # ------------------------------------------------------------------
    def test_register_unknown_type_raises(self):
        """Неизвестный тип аспекта вызывает ValueError."""
        gate = AspectGate()
        with pytest.raises(ValueError, match="Неизвестный тип аспекта"):
            gate.register(DummyAspect(), description="x", type="unknown")

    def test_register_without_description_raises(self):
        """Отсутствие описания в metadata вызывает ValueError."""
        gate = AspectGate()
        with pytest.raises(ValueError, match="Missing required metadata key 'description'"):
            gate.register(DummyAspect(), type="regular")

    # ------------------------------------------------------------------
    # Удаление аспектов
    # ------------------------------------------------------------------
    def test_unregister_regular(self):
        """Удаление обычного аспекта."""
        gate = AspectGate()
        m1 = DummyAspect()
        m2 = DummyAspect()
        gate.register(m1, description="first", type="regular")
        gate.register(m2, description="second", type="regular")

        gate.unregister(m1)
        assert gate.get_regular() == [(m2, "second")]

    def test_unregister_summary(self):
        """Удаление summary-аспекта."""
        gate = AspectGate()
        m = DummyAspect()
        gate.register(m, description="summary", type="summary")
        gate.unregister(m)
        assert gate.get_summary() is None

    def test_unregister_nonexistent_ignored(self):
        """Удаление незарегистрированного аспекта не вызывает ошибку."""
        gate = AspectGate()
        gate.unregister(DummyAspect())  # не падает

    def test_unregister_does_not_affect_other_regular(self):
        """Удаление одного обычного аспекта не влияет на другие."""
        gate = AspectGate()
        m1 = DummyAspect()
        m2 = DummyAspect()
        gate.register(m1, description="first", type="regular")
        gate.register(m2, description="second", type="regular")

        gate.unregister(m2)
        assert gate.get_regular() == [(m1, "first")]

    # ------------------------------------------------------------------
    # Получение аспектов (возврат копий)
    # ------------------------------------------------------------------
    def test_get_regular_returns_copy(self):
        """get_regular возвращает копию списка, внешние изменения не влияют на шлюз."""
        gate = AspectGate()
        m = DummyAspect()
        gate.register(m, description="test", type="regular")

        regular = gate.get_regular()
        regular.append((DummyAspect(), "other"))

        assert gate.get_regular() == [(m, "test")]

    def test_get_summary_returns_tuple_or_none(self):
        """get_summary возвращает кортеж или None, не копируя (он неизменяем)."""
        gate = AspectGate()
        m = DummyAspect()
        gate.register(m, description="summary", type="summary")

        summary = gate.get_summary()
        assert summary == (m, "summary")
        # Попытка изменить кортеж не должна влиять на шлюз (но кортеж неизменяем)
        # Дополнительная проверка, что это тот же объект
        assert gate.get_summary() is summary

    # ------------------------------------------------------------------
    # Отсутствие заморозки (AspectGate не имеет _frozen, но если бы была,
    # мы бы проверили; пока просто удостоверимся, что регистрация всегда возможна)
    # ------------------------------------------------------------------
    def test_register_always_possible(self):
        """AspectGate не имеет заморозки, регистрация возможна в любое время."""
        gate = AspectGate()
        m1 = DummyAspect()
        gate.register(m1, description="first", type="regular")
        gate.register(DummyAspect(), description="second", type="regular")
        gate.register(DummyAspect(), description="summary", type="summary")

        # После регистрации summary можно добавить ещё regular
        gate.register(DummyAspect(), description="third", type="regular")
        assert len(gate.get_regular()) == 3
        assert gate.get_summary() is not None