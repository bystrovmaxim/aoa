# tests/core/test_writable_mixin.py
"""
Тесты WritableMixin — миксина для поддержки записи через __setitem__.

Проверяем:
- Установка атрибута через __setitem__
- Корректная работа с существующими и новыми атрибутами
"""


from action_machine.Core.WritableMixin import WritableMixin


class SampleWritable(WritableMixin):
    """Тестовый класс с WritableMixin."""
    def __init__(self):
        self.existing = "value"


class TestWritableMixin:
    """Тесты для WritableMixin."""

    def test_setitem_sets_existing_attribute(self):
        """__setitem__ изменяет существующий атрибут."""
        obj = SampleWritable()
        obj["existing"] = "new"

        assert obj.existing == "new"

    def test_setitem_creates_new_attribute(self):
        """__setitem__ создаёт новый атрибут, если его не было."""
        obj = SampleWritable()
        obj["new_attr"] = 42

        assert hasattr(obj, "new_attr")
        assert obj.new_attr == 42

    def test_setitem_with_different_types(self):
        """__setitem__ работает с любыми типами значений."""
        obj = SampleWritable()
        obj["int"] = 1
        obj["str"] = "text"
        obj["list"] = [1, 2, 3]
        obj["dict"] = {"a": 1}

        assert obj.int == 1
        assert obj.str == "text"
        assert obj.list == [1, 2, 3]
        assert obj.dict == {"a": 1}