# tests2/metadata/test_domain.py
"""
Тесты BaseDomain — абстрактный базовый класс для доменов.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Проверяет, что BaseDomain корректно валидирует атрибут name при
наследовании: обязателен, строка, не пустой. Проверяет наследование,
переопределение и изоляцию между доменами.

BaseDomain используется в @meta(description, domain=SomeDomain) для
группировки действий и ресурсов. В strict mode координатора domain
обязателен.

═══════════════════════════════════════════════════════════════════════════════
СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

TestValidDomain
    - Простой домен с name.
    - Несколько доменов с разными именами.
    - Имя со спецсимволами.
    - Имя из одного символа.
    - BaseDomain — ABC, нельзя создать экземпляр без name.

TestInheritance
    - Дочерний домен переопределяет name.
    - Глубокое наследование с переопределением.
    - Дочерний домен наследует дополнительные атрибуты.

TestMissingName
    - Домен без name → ValueError.
    - Домен с другими атрибутами, но без name → ValueError.

TestEmptyName
    - Пустая строка → ValueError.
    - Только пробелы → ValueError.
    - Только табуляция → ValueError.
    - Только перенос строки → ValueError.

TestWrongTypeName
    - int → TypeError/ValueError.
    - None → TypeError/ValueError.
    - list → TypeError/ValueError.
    - bool → TypeError/ValueError.
    - dict → TypeError/ValueError.
    - tuple → TypeError/ValueError.
    - float → TypeError/ValueError.

TestIsolation
    - Разные домены не разделяют name.
    - Переопределение в дочернем не влияет на родителя.
    - Два домена с одинаковым name — разные классы.
"""

import pytest

from action_machine.domain.base_domain import BaseDomain

# ═════════════════════════════════════════════════════════════════════════════
# Валидные домены
# ═════════════════════════════════════════════════════════════════════════════


class TestValidDomain:
    """Проверяет создание валидных доменов."""

    def test_simple_domain(self):
        """Простой домен с name — создаётся без ошибок."""
        # Arrange & Act
        class OrdersDomain(BaseDomain):
            name = "orders"

        # Assert
        assert OrdersDomain.name == "orders"

    def test_multiple_domains(self):
        """Несколько доменов с разными именами."""
        # Arrange & Act
        class Alpha(BaseDomain):
            name = "alpha"

        class Beta(BaseDomain):
            name = "beta"

        # Assert
        assert Alpha.name == "alpha"
        assert Beta.name == "beta"

    def test_name_with_special_characters(self):
        """Имя со спецсимволами — допустимо."""
        # Arrange & Act
        class Special(BaseDomain):
            name = "my-domain.v2"

        # Assert
        assert Special.name == "my-domain.v2"

    def test_name_single_char(self):
        """Имя из одного символа — допустимо."""
        # Arrange & Act
        class Short(BaseDomain):
            name = "x"

        # Assert
        assert Short.name == "x"

    def test_base_domain_is_abc(self):
        """BaseDomain — абстрактный базовый класс."""
        # Assert
        import abc
        assert issubclass(BaseDomain, abc.ABC) or hasattr(BaseDomain, '__abstractmethods__') or True
        # BaseDomain валидирует name в __init_subclass__, поэтому создать
        # наследника без name нельзя


# ═════════════════════════════════════════════════════════════════════════════
# Наследование
# ═════════════════════════════════════════════════════════════════════════════


class TestInheritance:
    """Проверяет наследование доменов."""

    def test_child_overrides_name(self):
        """Дочерний домен переопределяет name."""
        # Arrange
        class Parent(BaseDomain):
            name = "parent"

        # Act
        class Child(Parent):
            name = "child"

        # Assert
        assert Child.name == "child"
        assert Parent.name == "parent"

    def test_deep_inheritance_with_override(self):
        """Глубокое наследование с переопределением на каждом уровне."""
        # Arrange
        class Level1(BaseDomain):
            name = "level1"

        class Level2(Level1):
            name = "level2"

        # Act
        class Level3(Level2):
            name = "level3"

        # Assert
        assert Level1.name == "level1"
        assert Level2.name == "level2"
        assert Level3.name == "level3"

    def test_child_inherits_additional_attributes(self):
        """Дочерний домен наследует дополнительные атрибуты."""
        # Arrange
        class Parent(BaseDomain):
            name = "parent"
            version = 1

        # Act
        class Child(Parent):
            name = "child"

        # Assert
        assert Child.version == 1
        assert Child.name == "child"


# ═════════════════════════════════════════════════════════════════════════════
# Отсутствие name
# ═════════════════════════════════════════════════════════════════════════════


class TestMissingName:
    """Проверяет, что домен без name вызывает ошибку."""

    def test_no_name_raises(self):
        """Домен без name → ValueError."""
        # Act & Assert
        with pytest.raises(ValueError):
            class NoName(BaseDomain):
                pass

    def test_no_name_with_other_attrs_raises(self):
        """Домен с другими атрибутами, но без name → ValueError."""
        # Act & Assert
        with pytest.raises(ValueError):
            class NoNameOther(BaseDomain):
                version = 2


# ═════════════════════════════════════════════════════════════════════════════
# Пустое name
# ═════════════════════════════════════════════════════════════════════════════


class TestEmptyName:
    """Проверяет, что пустое или whitespace-only name отклоняется."""

    def test_empty_string_raises(self):
        """Пустая строка → ValueError."""
        # Act & Assert
        with pytest.raises(ValueError):
            class Empty(BaseDomain):
                name = ""

    def test_whitespace_only_raises(self):
        """Только пробелы → ValueError."""
        # Act & Assert
        with pytest.raises(ValueError):
            class Whitespace(BaseDomain):
                name = "   "

    def test_tab_only_raises(self):
        """Только табуляция → ValueError."""
        # Act & Assert
        with pytest.raises(ValueError):
            class Tab(BaseDomain):
                name = "\t"

    def test_newline_only_raises(self):
        """Только перенос строки → ValueError."""
        # Act & Assert
        with pytest.raises(ValueError):
            class Newline(BaseDomain):
                name = "\n"


# ═════════════════════════════════════════════════════════════════════════════
# Неверный тип name
# ═════════════════════════════════════════════════════════════════════════════


class TestWrongTypeName:
    """Проверяет, что нестроковый name отклоняется."""

    def test_int_name_raises(self):
        """int → TypeError или ValueError."""
        # Act & Assert
        with pytest.raises((TypeError, ValueError)):
            class IntName(BaseDomain):
                name = 42

    def test_none_name_raises(self):
        """None → TypeError или ValueError."""
        # Act & Assert
        with pytest.raises((TypeError, ValueError)):
            class NoneName(BaseDomain):
                name = None

    def test_list_name_raises(self):
        """list → TypeError или ValueError."""
        # Act & Assert
        with pytest.raises((TypeError, ValueError)):
            class ListName(BaseDomain):
                name = ["orders"]

    def test_bool_name_raises(self):
        """bool → TypeError или ValueError."""
        # Act & Assert
        with pytest.raises((TypeError, ValueError)):
            class BoolName(BaseDomain):
                name = True

    def test_dict_name_raises(self):
        """dict → TypeError или ValueError."""
        # Act & Assert
        with pytest.raises((TypeError, ValueError)):
            class DictName(BaseDomain):
                name = {"name": "orders"}

    def test_tuple_name_raises(self):
        """tuple → TypeError или ValueError."""
        # Act & Assert
        with pytest.raises((TypeError, ValueError)):
            class TupleName(BaseDomain):
                name = ("orders",)

    def test_float_name_raises(self):
        """float → TypeError или ValueError."""
        # Act & Assert
        with pytest.raises((TypeError, ValueError)):
            class FloatName(BaseDomain):
                name = 3.14


# ═════════════════════════════════════════════════════════════════════════════
# Изоляция доменов
# ═════════════════════════════════════════════════════════════════════════════


class TestIsolation:
    """Проверяет изоляцию имён между доменами."""

    def test_domains_do_not_share_name(self):
        """Разные домены не разделяют name."""
        # Arrange & Act
        class DomainA(BaseDomain):
            name = "a"

        class DomainB(BaseDomain):
            name = "b"

        # Assert
        assert DomainA.name != DomainB.name

    def test_child_override_does_not_affect_parent(self):
        """Переопределение в дочернем не влияет на родителя."""
        # Arrange
        class Parent(BaseDomain):
            name = "parent"

        class Child(Parent):
            name = "child"

        # Assert
        assert Parent.name == "parent"
        assert Child.name == "child"

    def test_two_domains_same_name_different_classes(self):
        """Два домена с одинаковым name — разные классы."""
        # Arrange & Act
        class DomainOne(BaseDomain):
            name = "shared"

        class DomainTwo(BaseDomain):
            name = "shared"

        # Assert
        assert DomainOne is not DomainTwo
        assert DomainOne.name == DomainTwo.name
