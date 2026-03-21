# tests/aspects/test_aspect_gate.py
"""
Tests for AspectGate — the aspect gate.

Updated to use get_regular() and get_summary() instead of removed get_components().
"""

import pytest

from action_machine.aspects.aspect_gate import AspectGate


class DummyAspect:
    """Stub for aspect method."""
    async def __call__(self, *args, **kwargs):
        pass


class TestAspectGate:
    def test_register_regular(self):
        gate = AspectGate()
        method = DummyAspect()
        gate.register(method, description="test", type="regular")
        assert gate.get_regular() == [(method, "test")]
        assert gate.get_summary() is None

    def test_register_summary(self):
        gate = AspectGate()
        method = DummyAspect()
        gate.register(method, description="summary", type="summary")
        assert gate.get_regular() == []
        assert gate.get_summary() == (method, "summary")

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

    def test_unregister_summary(self):
        gate = AspectGate()
        m = DummyAspect()
        gate.register(m, description="s", type="summary")
        gate.unregister(m)
        assert gate.get_summary() is None

    def test_unregister_nonexistent_ignored(self):
        gate = AspectGate()
        gate.unregister(DummyAspect())  # no error

    def test_regular_aspects_order(self):
        """Regular aspects are returned in registration order."""
        gate = AspectGate()
        m1 = DummyAspect()
        m2 = DummyAspect()
        gate.register(m1, description="first", type="regular")
        gate.register(m2, description="second", type="regular")
        regular = gate.get_regular()
        assert len(regular) == 2
        assert regular[0][0] is m1
        assert regular[1][0] is m2

    def test_get_regular_returns_copy(self):
        gate = AspectGate()
        m = DummyAspect()
        gate.register(m, description="test", type="regular")
        regular = gate.get_regular()
        regular.append((DummyAspect(), "other"))
        assert gate.get_regular() == [(m, "test")]  # original unchanged