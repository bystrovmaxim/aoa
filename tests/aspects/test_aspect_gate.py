# tests/aspects/test_aspect_gate.py
"""
Тесты для AspectGate — шлюза аспектов.
"""

import pytest

from action_machine.aspects.aspect_gate import AspectGate


class DummyAspect:
    """Заглушка для метода-аспекта."""
    async def __call__(self, *args, **kwargs):
        pass


class TestAspectGate:
    def test_register_regular(self):
        gate = AspectGate()
        method = DummyAspect()
        gate.register(method, description="test", type="regular")
        assert gate.get_regular() == [(method, "test")]
        assert gate.get_summary() is None
        assert gate.get_components() == [method]

    def test_register_summary(self):
        gate = AspectGate()
        method = DummyAspect()
        gate.register(method, description="summary", type="summary")
        assert gate.get_regular() == []
        assert gate.get_summary() == (method, "summary")
        assert gate.get_components() == [method]

    def test_register_unknown_type_raises(self):
        gate = AspectGate()
        with pytest.raises(ValueError, match="Неизвестный тип аспекта"):
            gate.register(DummyAspect(), description="x", type="unknown")

    def test_register_two_summaries_raises(self):
        gate = AspectGate()
        gate.register(DummyAspect(), description="first", type="summary")
        with pytest.raises(ValueError, match="Разрешён только один summary-аспект"):
            gate.register(DummyAspect(), description="second", type="summary")

    def test_unregister_regular(self):
        gate = AspectGate()
        m1 = DummyAspect()
        m2 = DummyAspect()
        gate.register(m1, description="a", type="regular")
        gate.register(m2, description="b", type="regular")
        gate.unregister(m1)
        assert gate.get_regular() == [(m2, "b")]
        assert gate.get_components() == [m2]

    def test_unregister_summary(self):
        gate = AspectGate()
        m = DummyAspect()
        gate.register(m, description="s", type="summary")
        gate.unregister(m)
        assert gate.get_summary() is None
        assert gate.get_components() == []

    def test_unregister_nonexistent_ignored(self):
        gate = AspectGate()
        gate.unregister(DummyAspect())  # не должно быть ошибки

    def test_get_components_order(self):
        gate = AspectGate()
        r1 = DummyAspect()
        r2 = DummyAspect()
        s = DummyAspect()
        gate.register(r1, description="r1", type="regular")
        gate.register(s, description="s", type="summary")
        gate.register(r2, description="r2", type="regular")
        assert gate.get_components() == [r1, r2, s]

    def test_get_regular_returns_copy(self):
        gate = AspectGate()
        m = DummyAspect()
        gate.register(m, description="test", type="regular")
        regular = gate.get_regular()
        regular.append((DummyAspect(), "other"))
        assert gate.get_regular() == [(m, "test")]  # исходный не изменился