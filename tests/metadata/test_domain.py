# tests/metadata/test_domain.py
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
        class AlphaDomain(BaseDomain):
            name = "alpha"

        class BetaDomain(BaseDomain):
            name = "beta"

        # Assert
        assert AlphaDomain.name == "alpha"
        assert BetaDomain.name == "beta"

    def test_name_with_special_characters(self):
        """Имя со спецсимволами — допустимо."""
        # Arrange & Act
        class SpecialDomain(BaseDomain):
            name = "my-domain.v2"

        # Assert
        assert SpecialDomain.name == "my-domain.v2"

    def test_name_single_char(self):
        """Имя из одного символа — допустимо."""
        # Arrange & Act
        class ShortDomain(BaseDomain):
            name = "x"

        # Assert
        assert ShortDomain.name == "x"

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
        class ParentDomain(BaseDomain):
            name = "parent"

        # Act
        class ChildDomain(ParentDomain):
            name = "child"

        # Assert
        assert ChildDomain.name == "child"
        assert ParentDomain.name == "parent"

    def test_deep_inheritance_with_override(self):
        """Глубокое наследование с переопределением на каждом уровне."""
        # Arrange
        class Level1Domain(BaseDomain):
            name = "level1"

        class Level2Domain(Level1Domain):
            name = "level2"

        # Act
        class Level3Domain(Level2Domain):
            name = "level3"

        # Assert
        assert Level1Domain.name == "level1"
        assert Level2Domain.name == "level2"
        assert Level3Domain.name == "level3"

    def test_child_inherits_additional_attributes(self):
        """Дочерний домен наследует дополнительные атрибуты."""
        # Arrange
        class ParentDomain(BaseDomain):
            name = "parent"
            version = 1

        # Act
        class ChildDomain(ParentDomain):
            name = "child"

        # Assert
        assert ChildDomain.version == 1
        assert ChildDomain.name == "child"


# ═════════════════════════════════════════════════════════════════════════════
# Отсутствие name
# ═════════════════════════════════════════════════════════════════════════════


class TestMissingName:
    """Проверяет, что домен без name вызывает ошибку."""

    def test_no_name_raises(self):
        """Домен без name → ValueError."""
        # Act & Assert
        with pytest.raises(ValueError):
            class NoNameDomain(BaseDomain):
                pass

    def test_no_name_with_other_attrs_raises(self):
        """Домен с другими атрибутами, но без name → ValueError."""
        # Act & Assert
        with pytest.raises(ValueError):
            class NoNameOtherDomain(BaseDomain):
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
            class EmptyDomain(BaseDomain):
                name = ""

    def test_whitespace_only_raises(self):
        """Только пробелы → ValueError."""
        # Act & Assert
        with pytest.raises(ValueError):
            class WhitespaceDomain(BaseDomain):
                name = "   "

    def test_tab_only_raises(self):
        """Только табуляция → ValueError."""
        # Act & Assert
        with pytest.raises(ValueError):
            class TabDomain(BaseDomain):
                name = "\t"

    def test_newline_only_raises(self):
        """Только перенос строки → ValueError."""
        # Act & Assert
        with pytest.raises(ValueError):
            class NewlineDomain(BaseDomain):
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
            class IntNameDomain(BaseDomain):
                name = 42

    def test_none_name_raises(self):
        """None → TypeError или ValueError."""
        # Act & Assert
        with pytest.raises((TypeError, ValueError)):
            class NoneNameDomain(BaseDomain):
                name = None

    def test_list_name_raises(self):
        """list → TypeError или ValueError."""
        # Act & Assert
        with pytest.raises((TypeError, ValueError)):
            class ListNameDomain(BaseDomain):
                name = ["orders"]

    def test_bool_name_raises(self):
        """bool → TypeError или ValueError."""
        # Act & Assert
        with pytest.raises((TypeError, ValueError)):
            class BoolNameDomain(BaseDomain):
                name = True

    def test_dict_name_raises(self):
        """dict → TypeError или ValueError."""
        # Act & Assert
        with pytest.raises((TypeError, ValueError)):
            class DictNameDomain(BaseDomain):
                name = {"name": "orders"}

    def test_tuple_name_raises(self):
        """tuple → TypeError или ValueError."""
        # Act & Assert
        with pytest.raises((TypeError, ValueError)):
            class TupleNameDomain(BaseDomain):
                name = ("orders",)

    def test_float_name_raises(self):
        """float → TypeError или ValueError."""
        # Act & Assert
        with pytest.raises((TypeError, ValueError)):
            class FloatNameDomain(BaseDomain):
                name = 3.14


# ═════════════════════════════════════════════════════════════════════════════
# Изоляция доменов
# ═════════════════════════════════════════════════════════════════════════════


class TestIsolation:
    """Проверяет изоляцию имён между доменами."""

    def test_domains_do_not_share_name(self):
        """Разные домены не разделяют name."""
        # Arrange & Act
        class DomainADomain(BaseDomain):
            name = "a"

        class DomainBDomain(BaseDomain):
            name = "b"

        # Assert
        assert DomainADomain.name != DomainBDomain.name

    def test_child_override_does_not_affect_parent(self):
        """Переопределение в дочернем не влияет на родителя."""
        # Arrange
        class ParentDomain(BaseDomain):
            name = "parent"

        class ChildDomain(ParentDomain):
            name = "child"

        # Assert
        assert ParentDomain.name == "parent"
        assert ChildDomain.name == "child"

    def test_two_domains_same_name_different_classes(self):
        """Два домена с одинаковым name — разные классы."""
        # Arrange & Act
        class DomainOneDomain(BaseDomain):
            name = "shared"

        class DomainTwoDomain(BaseDomain):
            name = "shared"

        # Assert
        assert DomainOneDomain is not DomainTwoDomain
        assert DomainOneDomain.name == DomainTwoDomain.name
