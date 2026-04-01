# tests2/decorators/test_meta_decorator.py
"""
Тесты декоратора @meta — описание и доменная принадлежность класса.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Декоратор @meta объявляет обязательное текстовое описание класса и
опциональную привязку к бизнес-домену. Применяется к двум типам классов:

1. Действия (Action) — через ActionMetaGateHost в BaseAction.
2. Ресурсные менеджеры (ResourceManager) — через ResourceMetaGateHost
   в BaseResourceManager.

При применении декоратор записывает словарь _meta_info в целевой класс:
    {"description": str, "domain": type[BaseDomain] | None}

MetadataBuilder читает _meta_info при сборке ClassMetadata.meta (MetaInfo).

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

Валидные аргументы:
    - description — непустая строка.
    - domain — подкласс BaseDomain или None.
    - description + domain — оба заданы.

Запись _meta_info:
    - Декоратор записывает description и domain в cls._meta_info.
    - Класс возвращается без изменений.

Невалидные аргументы:
    - description не строка → TypeError.
    - description пустая или из пробелов → ValueError.
    - domain не подкласс BaseDomain и не None → TypeError.

Невалидные цели:
    - Применён к функции → TypeError.
    - Класс не наследует ни ActionMetaGateHost, ни ResourceMetaGateHost → TypeError.

Обязательность @meta:
    - Action с аспектами без @meta → TypeError при сборке метаданных.
    - ResourceManager без @meta → TypeError при сборке метаданных.

Интеграция:
    - MetadataBuilder собирает MetaInfo из _meta_info.
    - GateCoordinator обогащает граф описанием и доменом.
"""

import pytest

from action_machine.aspects.summary_aspect import summary_aspect
from action_machine.auth import ROLE_NONE, check_roles
from action_machine.core.base_action import BaseAction
from action_machine.core.base_params import BaseParams
from action_machine.core.base_result import BaseResult
from action_machine.core.gate_coordinator import GateCoordinator
from action_machine.core.meta_decorator import meta
from action_machine.domain.base_domain import BaseDomain
from action_machine.resource_managers.base_resource_manager import BaseResourceManager

# ═════════════════════════════════════════════════════════════════════════════
# Вспомогательные домены для тестов
# ═════════════════════════════════════════════════════════════════════════════


class _TestDomain(BaseDomain):
    name = "test_domain"


class _OrdersDomain(BaseDomain):
    name = "orders"


# ═════════════════════════════════════════════════════════════════════════════
# Валидные аргументы
# ═════════════════════════════════════════════════════════════════════════════


class TestValidArgs:
    """Декоратор принимает валидные аргументы и записывает _meta_info."""

    def test_description_only(self) -> None:
        """
        @meta(description="...") без domain — domain=None в _meta_info.

        Минимальный вызов: только описание, без привязки к домену.
        """
        # Arrange & Act
        @meta(description="Проверка доступности")
        @check_roles(ROLE_NONE)
        class _Action(BaseAction[BaseParams, BaseResult]):
            @summary_aspect("test")
            async def summary(self, params, state, box, connections):
                return BaseResult()

        # Assert — _meta_info записан с description и domain=None
        assert hasattr(_Action, "_meta_info")
        assert _Action._meta_info["description"] == "Проверка доступности"
        assert _Action._meta_info["domain"] is None

    def test_description_with_domain(self) -> None:
        """
        @meta(description="...", domain=TestDomain) — оба параметра.

        domain используется GateCoordinator для создания узла домена
        и ребра belongs_to в графе.
        """
        # Arrange & Act
        @meta(description="Создание заказа", domain=_OrdersDomain)
        @check_roles(ROLE_NONE)
        class _Action(BaseAction[BaseParams, BaseResult]):
            @summary_aspect("test")
            async def summary(self, params, state, box, connections):
                return BaseResult()

        # Assert — оба поля записаны
        assert _Action._meta_info["description"] == "Создание заказа"
        assert _Action._meta_info["domain"] is _OrdersDomain

    def test_returns_class_unchanged(self) -> None:
        """
        Декоратор возвращает класс без изменений.

        @meta не оборачивает класс — только записывает _meta_info.
        """
        # Arrange
        @check_roles(ROLE_NONE)
        class _Original(BaseAction[BaseParams, BaseResult]):
            custom = 42

            @summary_aspect("test")
            async def summary(self, params, state, box, connections):
                return BaseResult()

        # Act
        _Decorated = meta(description="Описание")(_Original)

        # Assert — тот же класс
        assert _Decorated is _Original
        assert _Decorated.custom == 42

    def test_on_resource_manager(self) -> None:
        """
        @meta на наследнике BaseResourceManager — валидная цель.

        BaseResourceManager наследует ResourceMetaGateHost,
        поэтому @meta допустим.
        """
        # Arrange & Act
        @meta(description="Менеджер PostgreSQL")
        class _Manager(BaseResourceManager):
            def get_wrapper_class(self):
                return None

        # Assert — _meta_info записан
        assert _Manager._meta_info["description"] == "Менеджер PostgreSQL"


# ═════════════════════════════════════════════════════════════════════════════
# Невалидные аргументы
# ═════════════════════════════════════════════════════════════════════════════


class TestInvalidArgs:
    """Невалидные аргументы → TypeError или ValueError."""

    def test_description_not_string_raises_type_error(self) -> None:
        """
        @meta(description=42) → TypeError.

        description обязан быть строкой.
        """
        # Arrange & Act & Assert
        with pytest.raises(TypeError, match="строкой"):
            meta(description=42)

    def test_description_empty_raises_value_error(self) -> None:
        """
        @meta(description="") → ValueError.

        Пустая строка не является описанием.
        """
        # Arrange & Act & Assert
        with pytest.raises(ValueError, match="пустой строкой"):
            meta(description="")

    def test_description_whitespace_raises_value_error(self) -> None:
        """
        @meta(description="   ") → ValueError.

        Строка из пробелов считается пустой после strip().
        """
        # Arrange & Act & Assert
        with pytest.raises(ValueError, match="пустой строкой"):
            meta(description="   ")

    def test_domain_not_base_domain_raises_type_error(self) -> None:
        """
        @meta(description="...", domain=str) → TypeError.

        domain должен быть подклассом BaseDomain или None.
        """
        # Arrange & Act & Assert
        with pytest.raises(TypeError, match="подклассом BaseDomain"):
            meta(description="Описание", domain=str)

    def test_domain_instance_raises_type_error(self) -> None:
        """
        @meta(description="...", domain="orders") → TypeError.

        domain — класс, не строка. Строковые домены не допускаются.
        """
        # Arrange & Act & Assert
        with pytest.raises(TypeError, match="подклассом BaseDomain"):
            meta(description="Описание", domain="orders")


# ═════════════════════════════════════════════════════════════════════════════
# Невалидные цели
# ═════════════════════════════════════════════════════════════════════════════


class TestInvalidTarget:
    """Декоратор применён к невалидной цели → TypeError."""

    def test_applied_to_function_raises_type_error(self) -> None:
        """
        @meta на функции → TypeError.

        @meta — декоратор уровня класса, не метода.
        """
        # Arrange & Act & Assert
        with pytest.raises(TypeError, match="только к классу"):
            @meta(description="Описание")
            def _func():
                pass

    def test_applied_to_plain_class_raises_type_error(self) -> None:
        """
        @meta на классе без ActionMetaGateHost и ResourceMetaGateHost → TypeError.

        Только наследники BaseAction и BaseResourceManager допускают @meta.
        """
        # Arrange & Act & Assert
        with pytest.raises(TypeError, match="не наследует"):
            @meta(description="Описание")
            class _Plain:
                pass

    def test_applied_to_instance_raises_type_error(self) -> None:
        """
        meta(description="...")(instance) → TypeError.
        """
        # Arrange
        class _Cls(BaseResourceManager):
            def get_wrapper_class(self):
                return None

        instance = _Cls()

        # Act & Assert
        with pytest.raises(TypeError, match="только к классу"):
            meta(description="Описание")(instance)


# ═════════════════════════════════════════════════════════════════════════════
# Обязательность @meta при сборке метаданных
# ═════════════════════════════════════════════════════════════════════════════


class TestMetaRequired:
    """MetadataBuilder требует @meta для Action с аспектами и ResourceManager."""

    def test_action_with_aspects_without_meta_raises(self) -> None:
        """
        Action с аспектами без @meta → TypeError при сборке метаданных.

        MetadataBuilder.build() проверяет: если класс наследует
        ActionMetaGateHost и содержит аспекты — @meta обязателен.
        """
        # Arrange — Action без @meta
        @check_roles(ROLE_NONE)
        class _NoMetaAction(BaseAction[BaseParams, BaseResult]):
            @summary_aspect("test")
            async def summary(self, params, state, box, connections):
                return BaseResult()

        coordinator = GateCoordinator()

        # Act & Assert — TypeError при сборке
        with pytest.raises(TypeError, match="не имеет декоратора @meta"):
            coordinator.get(_NoMetaAction)

    def test_resource_manager_without_meta_raises(self) -> None:
        """
        ResourceManager без @meta → TypeError при сборке метаданных.
        """
        # Arrange — ResourceManager без @meta
        class _NoMetaManager(BaseResourceManager):
            def get_wrapper_class(self):
                return None

        coordinator = GateCoordinator()

        # Act & Assert — TypeError при сборке
        with pytest.raises(TypeError, match="не имеет декоратора @meta"):
            coordinator.get(_NoMetaManager)


# ═════════════════════════════════════════════════════════════════════════════
# Интеграция с MetadataBuilder и GateCoordinator
# ═════════════════════════════════════════════════════════════════════════════


class TestMetadataIntegration:
    """_meta_info корректно собирается в ClassMetadata.meta (MetaInfo)."""

    def test_metadata_contains_description(self) -> None:
        """
        ClassMetadata.meta.description содержит текст из @meta.
        """
        # Arrange
        @meta(description="Тестовое действие")
        @check_roles(ROLE_NONE)
        class _Action(BaseAction[BaseParams, BaseResult]):
            @summary_aspect("test")
            async def summary(self, params, state, box, connections):
                return BaseResult()

        coordinator = GateCoordinator()

        # Act
        metadata = coordinator.get(_Action)

        # Assert
        assert metadata.has_meta()
        assert metadata.meta is not None
        assert metadata.meta.description == "Тестовое действие"

    def test_metadata_contains_domain(self) -> None:
        """
        ClassMetadata.meta.domain содержит класс домена из @meta.
        """
        # Arrange
        @meta(description="Действие с доменом", domain=_TestDomain)
        @check_roles(ROLE_NONE)
        class _Action(BaseAction[BaseParams, BaseResult]):
            @summary_aspect("test")
            async def summary(self, params, state, box, connections):
                return BaseResult()

        coordinator = GateCoordinator()

        # Act
        metadata = coordinator.get(_Action)

        # Assert
        assert metadata.meta is not None
        assert metadata.meta.domain is _TestDomain
        assert metadata.meta.domain.name == "test_domain"

    def test_metadata_domain_none_when_not_specified(self) -> None:
        """
        ClassMetadata.meta.domain=None когда domain не указан в @meta.
        """
        # Arrange
        @meta(description="Без домена")
        @check_roles(ROLE_NONE)
        class _Action(BaseAction[BaseParams, BaseResult]):
            @summary_aspect("test")
            async def summary(self, params, state, box, connections):
                return BaseResult()

        coordinator = GateCoordinator()

        # Act
        metadata = coordinator.get(_Action)

        # Assert
        assert metadata.meta is not None
        assert metadata.meta.domain is None
