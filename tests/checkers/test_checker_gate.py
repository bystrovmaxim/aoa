# tests/checkers/test_checker_gate.py
"""
Тесты для CheckerGate — шлюза управления чекерами полей.

Проверяем:
- Регистрацию классовых чекеров (target_type='class')
- Регистрацию методных чекеров (target_type='method')
- Поддержку нескольких чекеров на одно поле (порядок сохраняется)
- Получение чекеров через get_components(), get_class_checkers(), get_method_checkers()
- Удаление чекеров (unregister)
- Заморозку шлюза (freeze)
- Обработку ошибок (неверный target_type, отсутствие метода)
- Сбор чекеров через CheckerGateHost (миксин)

Изменения:
- Исправлен тест `test_get_all_method_checkers_returns_all_method_checkers`:
  лямбда-выражение заменено на обычную функцию для соответствия требованиям линтера.
- Обновлены комментарии.
"""

import pytest

from action_machine.Checkers.BaseFieldChecker import BaseFieldChecker
from action_machine.Checkers.checker_gate import CheckerGate


# ----------------------------------------------------------------------
# Тестовые чекеры
# ----------------------------------------------------------------------
class DummyChecker(BaseFieldChecker):
    """Фиктивный чекер для тестов (всегда успешен)."""

    def __init__(self, field_name: str, desc: str = ""):
        super().__init__(field_name, required=True, desc=desc)

    def _check_type_and_constraints(self, value):
        pass


def dummy_method():
    """Фиктивный метод для регистрации методных чекеров."""
    pass


# ======================================================================
# Тесты
# ======================================================================

class TestCheckerGate:
    """Тесты для CheckerGate."""

    # ------------------------------------------------------------------
    # Регистрация классовых чекеров
    # ------------------------------------------------------------------
    def test_register_class_checker(self):
        """Регистрация классового чекера."""
        gate = CheckerGate()
        checker = DummyChecker("name")

        gate.register(checker, target_type="class")

        # Проверяем порядок
        assert gate.get_components() == [checker]
        # Проверяем индекс по полю
        class_checkers = gate.get_class_checkers("name")
        assert len(class_checkers) == 1
        assert class_checkers[0] is checker

    def test_register_multiple_class_checkers_same_field(self):
        """
        Регистрация нескольких классовых чекеров на одно поле.
        Порядок регистрации сохраняется.
        """
        gate = CheckerGate()
        checker1 = DummyChecker("name")
        checker2 = DummyChecker("name")

        gate.register(checker1, target_type="class")
        gate.register(checker2, target_type="class")

        # Общий список
        assert gate.get_components() == [checker1, checker2]

        # Чекеры для поля "name"
        class_checkers = gate.get_class_checkers("name")
        assert class_checkers == [checker1, checker2]

    def test_register_class_checkers_different_fields(self):
        """Регистрация классовых чекеров на разные поля."""
        gate = CheckerGate()
        checker1 = DummyChecker("name")
        checker2 = DummyChecker("age")

        gate.register(checker1, target_type="class")
        gate.register(checker2, target_type="class")

        assert gate.get_class_checkers("name") == [checker1]
        assert gate.get_class_checkers("age") == [checker2]
        assert gate.get_components() == [checker1, checker2]

    # ------------------------------------------------------------------
    # Регистрация методных чекеров
    # ------------------------------------------------------------------
    def test_register_method_checker(self):
        """Регистрация методного чекера."""
        gate = CheckerGate()
        checker = DummyChecker("result_field")
        method = dummy_method

        gate.register(checker, target_type="method", method=method)

        # Общий список
        assert gate.get_components() == [checker]

        # Чекеры для метода
        method_checkers = gate.get_method_checkers(method)
        assert len(method_checkers) == 1
        assert method_checkers[0] is checker

        # Чекеры для метода и поля
        field_checkers = gate.get_method_checkers(method, "result_field")
        assert field_checkers == [checker]

    def test_register_multiple_method_checkers_same_field(self):
        """
        Регистрация нескольких методных чекеров на одно поле.
        Порядок регистрации сохраняется.
        """
        gate = CheckerGate()
        checker1 = DummyChecker("field")
        checker2 = DummyChecker("field")
        method = dummy_method

        gate.register(checker1, target_type="method", method=method)
        gate.register(checker2, target_type="method", method=method)

        # Общий список
        assert gate.get_components() == [checker1, checker2]

        # Чекеры для метода и поля
        field_checkers = gate.get_method_checkers(method, "field")
        assert field_checkers == [checker1, checker2]

    def test_register_method_checkers_different_methods(self):
        """Регистрация методных чекеров для разных методов."""
        gate = CheckerGate()

        def method_a():
            pass

        def method_b():
            pass

        checker_a = DummyChecker("field")
        checker_b = DummyChecker("field")

        gate.register(checker_a, target_type="method", method=method_a)
        gate.register(checker_b, target_type="method", method=method_b)

        # Каждый метод получает свой чекер
        assert gate.get_method_checkers(method_a) == [checker_a]
        assert gate.get_method_checkers(method_b) == [checker_b]

    # ------------------------------------------------------------------
    # Получение чекеров
    # ------------------------------------------------------------------
    def test_get_components_returns_copy(self):
        """get_components() возвращает копию, внешние изменения не влияют на шлюз."""
        gate = CheckerGate()
        checker = DummyChecker("name")
        gate.register(checker, target_type="class")

        components = gate.get_components()
        components.append(DummyChecker("extra"))

        assert gate.get_components() == [checker]

    def test_get_class_checkers_without_field_returns_all(self):
        """get_class_checkers() без поля возвращает все классовые чекеры."""
        gate = CheckerGate()
        checker1 = DummyChecker("name")
        checker2 = DummyChecker("age")

        gate.register(checker1, target_type="class")
        gate.register(checker2, target_type="class")

        assert gate.get_class_checkers() == [checker1, checker2]

    def test_get_method_checkers_returns_empty_for_unknown_method(self):
        """Для неизвестного метода get_method_checkers() возвращает пустой список."""
        gate = CheckerGate()
        method = dummy_method
        assert gate.get_method_checkers(method) == []

    def test_get_all_method_checkers_returns_all_method_checkers(self):
        """get_all_method_checkers() возвращает все методные чекеры с метаданными."""
        gate = CheckerGate()
        checker1 = DummyChecker("field1")
        checker2 = DummyChecker("field2")
        method1 = dummy_method
        # Используем обычную функцию вместо lambda для соответствия линтеру
        def method2(): pass

        gate.register(checker1, target_type="method", method=method1)
        gate.register(checker2, target_type="method", method=method2)

        all_method_checkers = gate.get_all_method_checkers()
        assert len(all_method_checkers) == 2
        assert (method1, "field1", checker1) in all_method_checkers
        assert (method2, "field2", checker2) in all_method_checkers

    # ------------------------------------------------------------------
    # Удаление (unregister)
    # ------------------------------------------------------------------
    def test_unregister_raises_after_freeze(self):
        """После заморозки unregister выбрасывает RuntimeError."""
        gate = CheckerGate()
        checker = DummyChecker("name")
        gate.register(checker, target_type="class")
        gate.freeze()

        with pytest.raises(RuntimeError, match="CheckerGate is frozen"):
            gate.unregister(checker)

    def test_unregister_raises_before_freeze_if_implemented(self):
        """
        Если бы unregister был реализован, он бы выбрасывал ошибку при изменении,
        но на данный момент реализация пустая, и он ничего не делает.
        Тест проверяет, что вызов не вызывает ошибок до заморозки.
        """
        gate = CheckerGate()
        checker = DummyChecker("name")
        gate.register(checker, target_type="class")
        # Пока не заморожен, unregister не должен падать (даже если ничего не делает)
        gate.unregister(checker)
        # Чекер всё ещё зарегистрирован (так как удаление не реализовано)
        assert gate.get_components() == [checker]

    # ------------------------------------------------------------------
    # Заморозка
    # ------------------------------------------------------------------
    def test_freeze_disables_registration(self):
        """После freeze() регистрация новых чекеров запрещена."""
        gate = CheckerGate()
        gate.freeze()

        with pytest.raises(RuntimeError, match="CheckerGate is frozen"):
            gate.register(DummyChecker("name"), target_type="class")

    def test_freeze_idempotent(self):
        """Повторный вызов freeze() не вызывает ошибок."""
        gate = CheckerGate()
        gate.freeze()
        gate.freeze()  # не падает

    # ------------------------------------------------------------------
    # Обработка ошибок при регистрации
    # ------------------------------------------------------------------
    def test_register_without_target_type_raises(self):
        """Регистрация без target_type вызывает ValueError."""
        gate = CheckerGate()
        with pytest.raises(ValueError, match="metadata\\['target_type'\\] must be 'class' or 'method'"):
            gate.register(DummyChecker("name"))

    def test_register_with_invalid_target_type_raises(self):
        """Неверный target_type вызывает ValueError."""
        gate = CheckerGate()
        with pytest.raises(ValueError, match="metadata\\['target_type'\\] must be 'class' or 'method'"):
            gate.register(DummyChecker("name"), target_type="invalid")

    def test_register_method_without_method_raises(self):
        """Для method-типа обязательно указать method в metadata."""
        gate = CheckerGate()
        with pytest.raises(ValueError, match="metadata\\['method'\\] is required"):
            gate.register(DummyChecker("name"), target_type="method")


# ======================================================================
# Тесты для CheckerGateHost (миксин, который собирает чекеры)
# ======================================================================

class TestCheckerGateHost:
    """
    Тесты для CheckerGateHost — миксина, который присоединяет CheckerGate к классу.
    Проверяем:
    - Сбор классовых чекеров из _field_checkers
    - Сбор методных чекеров из _result_checkers методов
    - Заморозку шлюза после сборки
    - Отсутствие мутации родительских данных при наследовании
    """

    # ------------------------------------------------------------------
    # Тестовые классы
    # ------------------------------------------------------------------
    def test_class_checkers_are_collected(self):
        """Классовые чекеры из _field_checkers регистрируются в шлюзе."""
        from action_machine.Checkers.checker_gate_host import CheckerGateHost

        class MyClass(CheckerGateHost):
            _field_checkers = [DummyChecker("name"), DummyChecker("age")]

        gate = MyClass.get_checker_gate()
        # Шлюз должен содержать оба чекера с target_type='class'
        components = gate.get_components()
        assert len(components) == 2
        # Проверяем, что это именно те чекеры
        assert components[0] is MyClass._field_checkers[0]
        assert components[1] is MyClass._field_checkers[1]

    def test_method_checkers_are_collected(self):
        """
        Методные чекеры из _result_checkers методов регистрируются в шлюзе.
        Используем декоратор при определении метода, чтобы атрибут _result_checkers
        был добавлен до вызова __init_subclass__.
        """
        from action_machine.Checkers.checker_gate_host import CheckerGateHost

        class MyClass(CheckerGateHost):
            @staticmethod
            @DummyChecker("field", desc="Test checker")
            def my_method():
                pass

        gate = MyClass.get_checker_gate()
        # После сборки чекер должен быть зарегистрирован
        method_checkers = gate.get_method_checkers(MyClass.my_method, "field")
        assert len(method_checkers) == 1
        assert method_checkers[0].field_name == "field"

    def test_gate_is_frozen_after_collection(self):
        """После сбора шлюз замораживается, регистрация новых чекеров невозможна."""
        from action_machine.Checkers.checker_gate_host import CheckerGateHost

        class MyClass(CheckerGateHost):
            _field_checkers = [DummyChecker("name")]

        gate = MyClass.get_checker_gate()
        with pytest.raises(RuntimeError, match="CheckerGate is frozen"):
            gate.register(DummyChecker("new"), target_type="class")

    def test_inheritance_does_not_share_gate(self):
        """
        При наследовании каждый класс получает свой собственный шлюз,
        а не разделяет с родителем.
        """
        from action_machine.Checkers.checker_gate_host import CheckerGateHost

        class Parent(CheckerGateHost):
            _field_checkers = [DummyChecker("parent")]

        class Child(Parent):
            _field_checkers = [DummyChecker("child")]

        parent_gate = Parent.get_checker_gate()
        child_gate = Child.get_checker_gate()

        # Гейты разные
        assert parent_gate is not child_gate

        # У родителя только parent-чекер
        parent_checkers = parent_gate.get_class_checkers()
        assert len(parent_checkers) == 1
        assert parent_checkers[0].field_name == "parent"

        # У ребёнка только child-чекер (родительский не копируется)
        child_checkers = child_gate.get_class_checkers()
        assert len(child_checkers) == 1
        assert child_checkers[0].field_name == "child"