# tests/domain/test_base_domain.py
"""
Тесты для BaseDomain — абстрактного базового класса доменов.

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

Успешные:
- Создание конкретного домена с валидным name.
- Несколько доменов с разными именами.
- Name со спецсимволами (дефис, подчёркивание, точка).
- Name из одного символа.
- Наследование от конкретного домена (дочерний переопределяет name).
- Домен наследует ABC (isinstance-проверка).

Ошибки:
- Класс без name → ValueError.
- Пустой name ("") → ValueError.
- Пробельный name ("   ") → ValueError.
- Табуляции и переносы → ValueError.
- Нестроковый name (int, None, list, bool, dict, tuple, float) → TypeError.

Изоляция:
- Домены не влияют друг на друга.
- Переопределение name в потомке не меняет родителя.
- Два домена с одинаковым name — разные классы.
"""

from abc import ABC

import pytest

from action_machine.domain.base_domain import BaseDomain

# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Успешное создание доменов
# ═════════════════════════════════════════════════════════════════════════════


class TestBaseDomainSuccess:
    """Проверка корректного создания доменов."""

    def test_simple_domain(self):
        """Конкретный домен с валидным name создаётся без ошибок."""

        class OrdersDomain(BaseDomain):
            name = "orders"

        assert OrdersDomain.name == "orders"

    def test_multiple_domains(self):
        """Несколько доменов с разными именами сосуществуют."""

        class CrmDomain(BaseDomain):
            name = "crm"

        class WarehouseDomain(BaseDomain):
            name = "warehouse"

        class PaymentsDomain(BaseDomain):
            name = "payments"

        assert CrmDomain.name == "crm"
        assert WarehouseDomain.name == "warehouse"
        assert PaymentsDomain.name == "payments"

    def test_domain_name_with_special_characters(self):
        """Name может содержать дефисы, подчёркивания, точки."""

        class DashDomain(BaseDomain):
            name = "my-domain"

        class UnderscoreDomain(BaseDomain):
            name = "my_domain"

        class DotDomain(BaseDomain):
            name = "my.domain"

        assert DashDomain.name == "my-domain"
        assert UnderscoreDomain.name == "my_domain"
        assert DotDomain.name == "my.domain"

    def test_domain_name_single_char(self):
        """Name может быть одним символом."""

        class XDomain(BaseDomain):
            name = "x"

        assert XDomain.name == "x"

    def test_domain_is_abc(self):
        """BaseDomain наследует ABC."""

        assert issubclass(BaseDomain, ABC)

        class TestDomain(BaseDomain):
            name = "test"

        assert issubclass(TestDomain, ABC)
        assert issubclass(TestDomain, BaseDomain)


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Наследование доменов
# ═════════════════════════════════════════════════════════════════════════════


class TestBaseDomainInheritance:
    """Проверка наследования доменов."""

    def test_child_overrides_name(self):
        """Дочерний класс может переопределить name родителя."""

        class ParentDomain(BaseDomain):
            name = "parent"

        class ChildDomain(ParentDomain):
            name = "child"

        assert ParentDomain.name == "parent"
        assert ChildDomain.name == "child"

    def test_deep_inheritance_with_override(self):
        """Глубокая цепочка: каждый уровень переопределяет name."""

        class Level1(BaseDomain):
            name = "level1"

        class Level2(Level1):
            name = "level2"

        class Level3(Level2):
            name = "level3"

        assert Level1.name == "level1"
        assert Level2.name == "level2"
        assert Level3.name == "level3"

    def test_child_inherits_additional_attributes(self):
        """Дочерний класс наследует дополнительные атрибуты родителя."""

        class ParentDomain(BaseDomain):
            name = "parent"
            is_external = True
            priority = 1

        class ChildDomain(ParentDomain):
            name = "child"

        assert ChildDomain.is_external is True
        assert ChildDomain.priority == 1
        assert ChildDomain.name == "child"


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Ошибки — отсутствующий name
# ═════════════════════════════════════════════════════════════════════════════


class TestBaseDomainMissingName:
    """Проверка ошибок при отсутствии name."""

    def test_no_name_raises_value_error(self):
        """Класс без name вызывает ValueError."""

        with pytest.raises(ValueError, match="не определяет атрибут 'name'"):
            class BadDomain(BaseDomain):
                pass

    def test_no_name_with_other_attrs_raises(self):
        """Класс с другими атрибутами, но без name → ValueError."""

        with pytest.raises(ValueError, match="не определяет атрибут 'name'"):
            class AlmostDomain(BaseDomain):
                priority = 1
                is_active = True


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Ошибки — пустой name
# ═════════════════════════════════════════════════════════════════════════════


class TestBaseDomainEmptyName:
    """Проверка ошибок при пустом name."""

    def test_empty_string_raises(self):
        """Пустая строка → ValueError."""

        with pytest.raises(ValueError, match="не может быть пустой строкой"):
            class EmptyDomain(BaseDomain):
                name = ""

    def test_whitespace_only_raises(self):
        """Строка из пробелов → ValueError."""

        with pytest.raises(ValueError, match="не может быть пустой строкой"):
            class SpaceDomain(BaseDomain):
                name = "   "

    def test_tab_only_raises(self):
        """Строка из табуляций → ValueError."""

        with pytest.raises(ValueError, match="не может быть пустой строкой"):
            class TabDomain(BaseDomain):
                name = "\t\t"

    def test_newline_only_raises(self):
        """Строка из переносов строк → ValueError."""

        with pytest.raises(ValueError, match="не может быть пустой строкой"):
            class NewlineDomain(BaseDomain):
                name = "\n\n"


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Ошибки — нестроковый name
# ═════════════════════════════════════════════════════════════════════════════


class TestBaseDomainWrongTypeName:
    """Проверка ошибок при нестроковом name."""

    def test_int_name_raises(self):
        """Число вместо строки → TypeError."""

        with pytest.raises(TypeError, match="должен быть строкой.*получен int"):
            class IntDomain(BaseDomain):
                name = 42

    def test_none_name_raises(self):
        """None вместо строки → TypeError."""

        with pytest.raises(TypeError, match="должен быть строкой.*получен NoneType"):
            class NoneDomain(BaseDomain):
                name = None

    def test_list_name_raises(self):
        """Список вместо строки → TypeError."""

        with pytest.raises(TypeError, match="должен быть строкой.*получен list"):
            class ListDomain(BaseDomain):
                name = ["orders"]

    def test_bool_name_raises(self):
        """
        Булево значение вместо строки → TypeError.
        bool является подклассом int, но не str.
        """

        with pytest.raises(TypeError, match="должен быть строкой.*получен bool"):
            class BoolDomain(BaseDomain):
                name = True

    def test_dict_name_raises(self):
        """Словарь вместо строки → TypeError."""

        with pytest.raises(TypeError, match="должен быть строкой.*получен dict"):
            class DictDomain(BaseDomain):
                name = {"domain": "orders"}

    def test_tuple_name_raises(self):
        """Кортеж вместо строки → TypeError."""

        with pytest.raises(TypeError, match="должен быть строкой.*получен tuple"):
            class TupleDomain(BaseDomain):
                name = ("orders",)

    def test_float_name_raises(self):
        """Число с плавающей точкой вместо строки → TypeError."""

        with pytest.raises(TypeError, match="должен быть строкой.*получен float"):
            class FloatDomain(BaseDomain):
                name = 3.14


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Изоляция доменов
# ═════════════════════════════════════════════════════════════════════════════


class TestBaseDomainIsolation:
    """Проверка, что домены изолированы друг от друга."""

    def test_domains_do_not_share_name(self):
        """Каждый домен имеет свой собственный name."""

        class DomainA(BaseDomain):
            name = "a"

        class DomainB(BaseDomain):
            name = "b"

        assert DomainA.name != DomainB.name
        assert DomainA.name == "a"
        assert DomainB.name == "b"

    def test_child_override_does_not_affect_parent(self):
        """Переопределение name в дочернем классе не меняет родителя."""

        class Parent(BaseDomain):
            name = "parent"

        class Child(Parent):
            name = "child"

        assert Parent.name == "parent"
        assert Child.name == "child"

    def test_two_domains_same_name_different_classes(self):
        """Два домена с одинаковым name — разные классы."""

        class Domain1(BaseDomain):
            name = "same"

        class Domain2(BaseDomain):
            name = "same"

        assert Domain1 is not Domain2
        assert Domain1.name == Domain2.name
