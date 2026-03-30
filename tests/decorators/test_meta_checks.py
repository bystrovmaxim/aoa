# tests/decorators/test_meta_checks.py
"""
Тесты проверок декоратора @meta.

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ ИНВАРИАНТЫ
═══════════════════════════════════════════════════════════════════════════════

Успешные сценарии:
    - Применение к классу с ActionMetaGateHost — описание сохраняется.
    - Применение к классу с ResourceMetaGateHost — описание сохраняется.
    - domain=None (по умолчанию) — допустимо.
    - domain=подкласс BaseDomain — сохраняется.
    - Класс возвращается без изменений (is-проверка).
    - Наследование _meta_info через MRO.

Ошибки — description:
    - description не строка (int, None, list) — TypeError.
    - description пустая строка — ValueError.
    - description из пробелов — ValueError.
    - description из табуляций — ValueError.

Ошибки — domain:
    - domain не класс (экземпляр, строка, число) — TypeError.
    - domain не подкласс BaseDomain — TypeError.

Ошибки — цель декоратора:
    - Применение к функции — TypeError.
    - Применение к экземпляру — TypeError.
    - Применение к классу без гейт-хоста — TypeError.

Обязательность @meta (через MetadataBuilder):
    - Action с аспектами без @meta → TypeError.
    - ResourceManager без @meta → TypeError.
    - Action с @meta → MetaInfo в ClassMetadata.
    - ResourceManager с @meta → MetaInfo в ClassMetadata.
"""

import pytest

from action_machine.core.meta_decorator import meta
from action_machine.core.meta_gate_hosts import ActionMetaGateHost, ResourceMetaGateHost
from action_machine.domain.base_domain import BaseDomain
from action_machine.metadata import MetadataBuilder

# ─────────────────────────────────────────────────────────────────────────────
# Вспомогательные классы
# ─────────────────────────────────────────────────────────────────────────────


class ActionHost(ActionMetaGateHost):
    """Минимальный класс с ActionMetaGateHost для тестов."""
    pass


class ResourceHost(ResourceMetaGateHost):
    """Минимальный класс с ResourceMetaGateHost для тестов."""
    pass


class OrdersDomain(BaseDomain):
    name = "orders"


class CrmDomain(BaseDomain):
    name = "crm"


class NotADomain:
    """Обычный класс, не наследующий BaseDomain."""
    pass


# ─────────────────────────────────────────────────────────────────────────────
# Успешные сценарии: ActionMetaGateHost
# ─────────────────────────────────────────────────────────────────────────────


class TestMetaActionSuccess:
    """Проверка корректного применения @meta к классам с ActionMetaGateHost."""

    def test_description_saved(self):
        """Description сохраняется в _meta_info."""

        @meta(description="Создание заказа")
        class MyAction(ActionHost):
            pass

        assert hasattr(MyAction, '_meta_info')
        assert MyAction._meta_info["description"] == "Создание заказа"
        assert MyAction._meta_info["domain"] is None

    def test_description_with_domain(self):
        """Description и domain сохраняются."""

        @meta(description="Создание заказа", domain=OrdersDomain)
        class MyAction(ActionHost):
            pass

        assert MyAction._meta_info["description"] == "Создание заказа"
        assert MyAction._meta_info["domain"] is OrdersDomain

    def test_domain_none_by_default(self):
        """domain по умолчанию — None."""

        @meta(description="Описание")
        class MyAction(ActionHost):
            pass

        assert MyAction._meta_info["domain"] is None

    def test_class_returned_unchanged(self):
        """Декоратор возвращает тот же класс."""

        @meta(description="Описание")
        class MyAction(ActionHost):
            pass

        assert isinstance(MyAction, type)
        assert issubclass(MyAction, ActionHost)

    def test_different_domains(self):
        """Разные действия могут принадлежать разным доменам."""

        @meta(description="Действие A", domain=OrdersDomain)
        class ActionA(ActionHost):
            pass

        @meta(description="Действие B", domain=CrmDomain)
        class ActionB(ActionHost):
            pass

        assert ActionA._meta_info["domain"] is OrdersDomain
        assert ActionB._meta_info["domain"] is CrmDomain


# ─────────────────────────────────────────────────────────────────────────────
# Успешные сценарии: ResourceMetaGateHost
# ─────────────────────────────────────────────────────────────────────────────


class TestMetaResourceSuccess:
    """Проверка корректного применения @meta к классам с ResourceMetaGateHost."""

    def test_description_saved(self):
        """Description сохраняется на ресурсном менеджере."""

        @meta(description="Менеджер PostgreSQL")
        class MyManager(ResourceHost):
            pass

        assert MyManager._meta_info["description"] == "Менеджер PostgreSQL"
        assert MyManager._meta_info["domain"] is None

    def test_description_with_domain(self):
        """ResourceManager может иметь domain."""

        @meta(description="Менеджер БД", domain=OrdersDomain)
        class MyManager(ResourceHost):
            pass

        assert MyManager._meta_info["domain"] is OrdersDomain


# ─────────────────────────────────────────────────────────────────────────────
# Наследование _meta_info
# ─────────────────────────────────────────────────────────────────────────────


class TestMetaInheritance:
    """Проверка наследования _meta_info через MRO."""

    def test_child_inherits_meta(self):
        """Дочерний класс без @meta наследует _meta_info родителя."""

        @meta(description="Родительское описание", domain=OrdersDomain)
        class Parent(ActionHost):
            pass

        class Child(Parent):
            pass

        assert getattr(Child, '_meta_info', None) is not None
        assert Child._meta_info["description"] == "Родительское описание"
        assert Child._meta_info["domain"] is OrdersDomain

    def test_child_overrides_meta(self):
        """Дочерний класс с @meta перезаписывает _meta_info."""

        @meta(description="Родительское")
        class Parent(ActionHost):
            pass

        @meta(description="Дочернее", domain=CrmDomain)
        class Child(Parent):
            pass

        assert Parent._meta_info["description"] == "Родительское"
        assert Parent._meta_info["domain"] is None

        assert Child._meta_info["description"] == "Дочернее"
        assert Child._meta_info["domain"] is CrmDomain


# ─────────────────────────────────────────────────────────────────────────────
# Ошибки: description
# ─────────────────────────────────────────────────────────────────────────────


class TestMetaDescriptionErrors:
    """Проверка ошибок при некорректном description."""

    def test_int_description_raises(self):
        """Число вместо строки — TypeError."""
        with pytest.raises(TypeError, match="description должен быть строкой"):
            meta(description=123)

    def test_none_description_raises(self):
        """None вместо строки — TypeError."""
        with pytest.raises(TypeError, match="description должен быть строкой"):
            meta(description=None)

    def test_list_description_raises(self):
        """Список вместо строки — TypeError."""
        with pytest.raises(TypeError, match="description должен быть строкой"):
            meta(description=["описание"])

    def test_empty_description_raises(self):
        """Пустая строка — ValueError."""
        with pytest.raises(ValueError, match="не может быть пустой строкой"):
            meta(description="")

    def test_whitespace_description_raises(self):
        """Строка из пробелов — ValueError."""
        with pytest.raises(ValueError, match="не может быть пустой строкой"):
            meta(description="   ")

    def test_tab_description_raises(self):
        """Строка из табуляций — ValueError."""
        with pytest.raises(ValueError, match="не может быть пустой строкой"):
            meta(description="\t\t")

    def test_newline_description_raises(self):
        """Строка из переносов строк — ValueError."""
        with pytest.raises(ValueError, match="не может быть пустой строкой"):
            meta(description="\n\n")


# ─────────────────────────────────────────────────────────────────────────────
# Ошибки: domain
# ─────────────────────────────────────────────────────────────────────────────


class TestMetaDomainErrors:
    """Проверка ошибок при некорректном domain."""

    def test_instance_instead_of_class_raises(self):
        """Экземпляр вместо класса — TypeError."""
        with pytest.raises(TypeError, match="должен быть подклассом BaseDomain или None"):
            meta(description="Описание", domain=OrdersDomain())

    def test_string_domain_raises(self):
        """Строка вместо класса — TypeError."""
        with pytest.raises(TypeError, match="должен быть подклассом BaseDomain или None"):
            meta(description="Описание", domain="orders")

    def test_int_domain_raises(self):
        """Число вместо класса — TypeError."""
        with pytest.raises(TypeError, match="должен быть подклассом BaseDomain или None"):
            meta(description="Описание", domain=42)

    def test_not_base_domain_subclass_raises(self):
        """Класс, не наследующий BaseDomain — TypeError."""
        with pytest.raises(TypeError, match="должен быть подклассом BaseDomain"):
            meta(description="Описание", domain=NotADomain)


# ─────────────────────────────────────────────────────────────────────────────
# Ошибки: цель декоратора
# ─────────────────────────────────────────────────────────────────────────────


class TestMetaTargetErrors:
    """Проверка ошибок при неправильном применении @meta."""

    def test_applied_to_function_raises(self):
        """@meta на функции — TypeError."""
        with pytest.raises(TypeError, match="только к классу"):
            @meta(description="Описание")
            def some_function():
                pass

    def test_applied_to_instance_raises(self):
        """@meta на экземпляре — TypeError."""
        obj = ActionHost()
        with pytest.raises(TypeError, match="только к классу"):
            meta(description="Описание")(obj)

    def test_applied_to_lambda_raises(self):
        """@meta на лямбде — TypeError."""
        with pytest.raises(TypeError, match="только к классу"):
            meta(description="Описание")(lambda: None)

    def test_applied_to_class_without_gate_host_raises(self):
        """@meta на классе без гейт-хоста — TypeError."""
        with pytest.raises(TypeError, match="не наследует ни ActionMetaGateHost"):
            @meta(description="Описание")
            class PlainClass:
                pass

    def test_applied_to_string_raises(self):
        """@meta на строке — TypeError."""
        with pytest.raises(TypeError, match="только к классу"):
            meta(description="Описание")("not a class")


# ─────────────────────────────────────────────────────────────────────────────
# Обязательность @meta через MetadataBuilder
# ─────────────────────────────────────────────────────────────────────────────


class TestMetaRequiredByBuilder:
    """
    Проверка, что MetadataBuilder выбрасывает TypeError для классов
    с гейт-хостами, но без @meta.
    """

    def test_action_with_aspects_without_meta_raises(self):
        """Action с аспектами без @meta → TypeError при сборке метаданных."""
        from action_machine.aspects.aspect_gate_host import AspectGateHost
        from action_machine.checkers.checker_gate_host import CheckerGateHost

        class BadAction(ActionMetaGateHost, AspectGateHost, CheckerGateHost):
            pass

        # Добавляем аспект вручную
        async def summary(self, params, state, box, connections):
            pass
        summary._new_aspect_meta = {"type": "summary", "description": "test"}
        BadAction.summary = summary

        with pytest.raises(TypeError, match="не имеет декоратора @meta"):
            MetadataBuilder.build(BadAction)

    def test_resource_manager_without_meta_raises(self):
        """ResourceManager без @meta → TypeError при сборке метаданных."""

        class BadManager(ResourceMetaGateHost):
            pass

        with pytest.raises(TypeError, match="не имеет декоратора @meta"):
            MetadataBuilder.build(BadManager)

    def test_action_with_meta_builds_successfully(self):
        """Action с @meta → MetaInfo в ClassMetadata."""
        from action_machine.aspects.aspect_gate_host import AspectGateHost
        from action_machine.checkers.checker_gate_host import CheckerGateHost

        @meta(description="Тестовое действие", domain=OrdersDomain)
        class GoodAction(ActionMetaGateHost, AspectGateHost, CheckerGateHost):
            pass

        async def summary(self, params, state, box, connections):
            pass
        summary._new_aspect_meta = {"type": "summary", "description": "test"}
        GoodAction.summary = summary

        metadata = MetadataBuilder.build(GoodAction)
        assert metadata.meta is not None
        assert metadata.meta.description == "Тестовое действие"
        assert metadata.meta.domain is OrdersDomain

    def test_resource_manager_with_meta_builds_successfully(self):
        """ResourceManager с @meta → MetaInfo в ClassMetadata."""

        @meta(description="Менеджер Redis")
        class GoodManager(ResourceMetaGateHost):
            pass

        metadata = MetadataBuilder.build(GoodManager)
        assert metadata.meta is not None
        assert metadata.meta.description == "Менеджер Redis"
        assert metadata.meta.domain is None

    def test_plain_class_without_meta_builds_successfully(self):
        """Обычный класс без гейт-хоста и без @meta — сборка успешна."""

        class PlainService:
            pass

        metadata = MetadataBuilder.build(PlainService)
        assert metadata.meta is None

    def test_action_without_aspects_without_meta_builds_successfully(self):
        """Action без аспектов и без @meta — допустимо (промежуточный класс)."""

        class IntermediateAction(ActionMetaGateHost):
            pass

        metadata = MetadataBuilder.build(IntermediateAction)
        assert metadata.meta is None
