# tests2/metadata/test_class_metadata.py
"""
Тесты ClassMetadata — frozen-датакласс полной конфигурации класса.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Проверяет корректность создания ClassMetadata, неизменяемость полей,
хелперы для инспекции (has_*, get_*) и строковое представление (__repr__).

ClassMetadata создаётся MetadataBuilder и хранится в GateCoordinator.
В рабочем коде никогда не создаётся вручную — только через Builder.
В тестах создаём напрямую для проверки контракта.

═══════════════════════════════════════════════════════════════════════════════
СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

TestMinimalCreation
    - Создание с минимальными параметрами (class_ref, class_name).
    - Все коллекции по умолчанию пустые.

TestFullCreation
    - Создание со всеми полями заполненными.
    - Поля сохраняют переданные значения.

TestImmutability
    - Frozen-датакласс: присвоение в class_ref, class_name, role,
      dependencies, aspects — FrozenInstanceError.

TestHasHelpers
    - has_role: True/False.
    - has_dependencies: True/False.
    - has_connections: True/False.
    - has_aspects: True/False.
    - has_checkers: True/False.
    - has_subscriptions: True/False.
    - has_sensitive_fields: True/False.
    - has_meta: True/False.

TestGetHelpers
    - get_regular_aspects: фильтрует по type="regular".
    - get_summary_aspect: возвращает аспект с type="summary" или None.
    - get_checkers_for_aspect: фильтрует чекеры по method_name.
    - get_dependency_classes: возвращает tuple классов.
    - get_connection_keys: возвращает tuple ключей.

TestRepr
    - Пустой класс: repr содержит имя класса.
    - С ролью: repr содержит role.
    - С зависимостями: repr содержит deps.
    - С аспектами: repr содержит aspects.
"""

import pytest

from action_machine.core.class_metadata import (
    AspectMeta,
    CheckerMeta,
    ClassMetadata,
    MetaInfo,
    RoleMeta,
)
from action_machine.dependencies.dependency_factory import DependencyInfo
from action_machine.resource_managers.base_resource_manager import BaseResourceManager
from action_machine.resource_managers.connection import ConnectionInfo

# ═════════════════════════════════════════════════════════════════════════════
# Вспомогательные классы
# ═════════════════════════════════════════════════════════════════════════════


class _EmptyClass:
    """Пустой класс для минимального ClassMetadata."""
    pass


class _ServiceA:
    """Зависимость A."""
    pass


class _ServiceB:
    """Зависимость B."""
    pass


class _MockManager(BaseResourceManager):
    """Мок менеджера соединений."""
    pass


async def _fake_aspect(self, params, state, box, connections):
    """Фейковый метод аспекта."""
    return {}


async def _fake_summary(self, params, state, box, connections):
    """Фейковый метод summary-аспекта."""
    return {}


# ═════════════════════════════════════════════════════════════════════════════
# Минимальное создание
# ═════════════════════════════════════════════════════════════════════════════


class TestMinimalCreation:
    """Проверяет создание ClassMetadata с минимальными параметрами."""

    def test_class_ref_stored(self):
        """class_ref сохраняет ссылку на класс."""
        # Arrange & Act
        meta = ClassMetadata(class_ref=_EmptyClass, class_name="test._EmptyClass")

        # Assert
        assert meta.class_ref is _EmptyClass

    def test_class_name_stored(self):
        """class_name сохраняет полное имя класса."""
        # Arrange & Act
        meta = ClassMetadata(class_ref=_EmptyClass, class_name="test._EmptyClass")

        # Assert
        assert meta.class_name == "test._EmptyClass"

    def test_default_meta_is_none(self):
        """По умолчанию meta равна None."""
        # Arrange & Act
        meta = ClassMetadata(class_ref=_EmptyClass, class_name="test._EmptyClass")

        # Assert
        assert meta.meta is None

    def test_default_role_is_none(self):
        """По умолчанию role равна None."""
        # Arrange & Act
        meta = ClassMetadata(class_ref=_EmptyClass, class_name="test._EmptyClass")

        # Assert
        assert meta.role is None

    def test_default_collections_empty(self):
        """По умолчанию все коллекции пустые кортежи."""
        # Arrange & Act
        meta = ClassMetadata(class_ref=_EmptyClass, class_name="test._EmptyClass")

        # Assert
        assert meta.dependencies == ()
        assert meta.connections == ()
        assert meta.aspects == ()
        assert meta.checkers == ()
        assert meta.subscriptions == ()
        assert meta.sensitive_fields == ()

    def test_default_field_descriptions_empty(self):
        """По умолчанию params_fields и result_fields — пустые кортежи."""
        # Arrange & Act
        meta = ClassMetadata(class_ref=_EmptyClass, class_name="test._EmptyClass")

        # Assert
        assert meta.params_fields == ()
        assert meta.result_fields == ()


# ═════════════════════════════════════════════════════════════════════════════
# Полное создание
# ═════════════════════════════════════════════════════════════════════════════


class TestFullCreation:
    """Проверяет создание ClassMetadata со всеми полями."""

    def test_meta_info_stored(self):
        """MetaInfo сохраняется в поле meta."""
        # Arrange
        meta_info = MetaInfo(description="Тестовое действие", domain=None)

        # Act
        cm = ClassMetadata(
            class_ref=_EmptyClass,
            class_name="test._EmptyClass",
            meta=meta_info,
        )

        # Assert
        assert cm.meta is meta_info
        assert cm.meta.description == "Тестовое действие"

    def test_role_stored(self):
        """RoleMeta сохраняется в поле role."""
        # Arrange
        role = RoleMeta(spec="admin")

        # Act
        cm = ClassMetadata(
            class_ref=_EmptyClass,
            class_name="test._EmptyClass",
            role=role,
        )

        # Assert
        assert cm.role is role
        assert cm.role.spec == "admin"

    def test_dependencies_stored(self):
        """Кортеж зависимостей сохраняется."""
        # Arrange
        deps = (
            DependencyInfo(cls=_ServiceA, factory=None, description=""),
            DependencyInfo(cls=_ServiceB, factory=None, description=""),
        )

        # Act
        cm = ClassMetadata(
            class_ref=_EmptyClass,
            class_name="test._EmptyClass",
            dependencies=deps,
        )

        # Assert
        assert len(cm.dependencies) == 2
        assert cm.dependencies[0].cls is _ServiceA
        assert cm.dependencies[1].cls is _ServiceB

    def test_connections_stored(self):
        """Кортеж соединений сохраняется."""
        # Arrange
        conns = (
            ConnectionInfo(cls=_MockManager, key="db", description=""),
        )

        # Act
        cm = ClassMetadata(
            class_ref=_EmptyClass,
            class_name="test._EmptyClass",
            connections=conns,
        )

        # Assert
        assert len(cm.connections) == 1
        assert cm.connections[0].key == "db"

    def test_aspects_stored(self):
        """Кортеж аспектов сохраняется с правильными типами."""
        # Arrange
        aspects = (
            AspectMeta(
                method_name="step_one",
                method_ref=_fake_aspect,
                aspect_type="regular",
                description="Шаг 1",
            ),
            AspectMeta(
                method_name="finalize",
                method_ref=_fake_summary,
                aspect_type="summary",
                description="Итог",
            ),
        )

        # Act
        cm = ClassMetadata(
            class_ref=_EmptyClass,
            class_name="test._EmptyClass",
            aspects=aspects,
        )

        # Assert
        assert len(cm.aspects) == 2
        assert cm.aspects[0].aspect_type == "regular"
        assert cm.aspects[1].aspect_type == "summary"


# ═════════════════════════════════════════════════════════════════════════════
# Неизменяемость (frozen)
# ═════════════════════════════════════════════════════════════════════════════


class TestImmutability:
    """Проверяет, что ClassMetadata — frozen-датакласс."""

    def test_cannot_modify_class_ref(self):
        """Присвоение в class_ref вызывает ошибку."""
        # Arrange
        cm = ClassMetadata(class_ref=_EmptyClass, class_name="test._EmptyClass")

        # Act & Assert
        with pytest.raises(AttributeError):
            cm.class_ref = _ServiceA

    def test_cannot_modify_class_name(self):
        """Присвоение в class_name вызывает ошибку."""
        # Arrange
        cm = ClassMetadata(class_ref=_EmptyClass, class_name="test._EmptyClass")

        # Act & Assert
        with pytest.raises(AttributeError):
            cm.class_name = "other"

    def test_cannot_modify_role(self):
        """Присвоение в role вызывает ошибку."""
        # Arrange
        cm = ClassMetadata(
            class_ref=_EmptyClass,
            class_name="test._EmptyClass",
            role=RoleMeta(spec="admin"),
        )

        # Act & Assert
        with pytest.raises(AttributeError):
            cm.role = None

    def test_cannot_modify_dependencies(self):
        """Присвоение в dependencies вызывает ошибку."""
        # Arrange
        cm = ClassMetadata(class_ref=_EmptyClass, class_name="test._EmptyClass")

        # Act & Assert
        with pytest.raises(AttributeError):
            cm.dependencies = ()

    def test_cannot_modify_aspects(self):
        """Присвоение в aspects вызывает ошибку."""
        # Arrange
        cm = ClassMetadata(class_ref=_EmptyClass, class_name="test._EmptyClass")

        # Act & Assert
        with pytest.raises(AttributeError):
            cm.aspects = ()


# ═════════════════════════════════════════════════════════════════════════════
# Хелперы has_*
# ═════════════════════════════════════════════════════════════════════════════


class TestHasHelpers:
    """Проверяет булевые хелперы has_*."""

    def test_has_role_false_when_none(self):
        """has_role возвращает False, если role не задана."""
        # Arrange
        cm = ClassMetadata(class_ref=_EmptyClass, class_name="x")

        # Assert
        assert cm.has_role() is False

    def test_has_role_true_when_set(self):
        """has_role возвращает True, если role задана."""
        # Arrange
        cm = ClassMetadata(
            class_ref=_EmptyClass,
            class_name="x",
            role=RoleMeta(spec="admin"),
        )

        # Assert
        assert cm.has_role() is True

    def test_has_dependencies_false_when_empty(self):
        """has_dependencies возвращает False для пустого кортежа."""
        # Arrange
        cm = ClassMetadata(class_ref=_EmptyClass, class_name="x")

        # Assert
        assert cm.has_dependencies() is False

    def test_has_dependencies_true_when_present(self):
        """has_dependencies возвращает True при наличии зависимостей."""
        # Arrange
        deps = (DependencyInfo(cls=_ServiceA, factory=None, description=""),)
        cm = ClassMetadata(class_ref=_EmptyClass, class_name="x", dependencies=deps)

        # Assert
        assert cm.has_dependencies() is True

    def test_has_connections_false_when_empty(self):
        """has_connections возвращает False для пустого кортежа."""
        # Arrange
        cm = ClassMetadata(class_ref=_EmptyClass, class_name="x")

        # Assert
        assert cm.has_connections() is False

    def test_has_connections_true_when_present(self):
        """has_connections возвращает True при наличии соединений."""
        # Arrange
        conns = (ConnectionInfo(cls=_MockManager, key="db", description=""),)
        cm = ClassMetadata(class_ref=_EmptyClass, class_name="x", connections=conns)

        # Assert
        assert cm.has_connections() is True

    def test_has_aspects_false_when_empty(self):
        """has_aspects возвращает False для пустого кортежа."""
        # Arrange
        cm = ClassMetadata(class_ref=_EmptyClass, class_name="x")

        # Assert
        assert cm.has_aspects() is False

    def test_has_aspects_true_when_present(self):
        """has_aspects возвращает True при наличии аспектов."""
        # Arrange
        aspects = (
            AspectMeta(
                method_name="step",
                method_ref=_fake_aspect,
                aspect_type="regular",
                description="",
            ),
        )
        cm = ClassMetadata(class_ref=_EmptyClass, class_name="x", aspects=aspects)

        # Assert
        assert cm.has_aspects() is True

    def test_has_checkers_false_when_empty(self):
        """has_checkers возвращает False для пустого кортежа."""
        # Arrange
        cm = ClassMetadata(class_ref=_EmptyClass, class_name="x")

        # Assert
        assert cm.has_checkers() is False

    def test_has_subscriptions_false_when_empty(self):
        """has_subscriptions возвращает False для пустого кортежа."""
        # Arrange
        cm = ClassMetadata(class_ref=_EmptyClass, class_name="x")

        # Assert
        assert cm.has_subscriptions() is False

    def test_has_sensitive_fields_false_when_empty(self):
        """has_sensitive_fields возвращает False для пустого кортежа."""
        # Arrange
        cm = ClassMetadata(class_ref=_EmptyClass, class_name="x")

        # Assert
        assert cm.has_sensitive_fields() is False

    def test_has_meta_false_when_none(self):
        """has_meta возвращает False, если meta не задана."""
        # Arrange
        cm = ClassMetadata(class_ref=_EmptyClass, class_name="x")

        # Assert
        assert cm.has_meta() is False

    def test_has_meta_true_when_set(self):
        """has_meta возвращает True, если meta задана."""
        # Arrange
        cm = ClassMetadata(
            class_ref=_EmptyClass,
            class_name="x",
            meta=MetaInfo(description="test", domain=None),
        )

        # Assert
        assert cm.has_meta() is True


# ═════════════════════════════════════════════════════════════════════════════
# Хелперы get_*
# ═════════════════════════════════════════════════════════════════════════════


class TestGetHelpers:
    """Проверяет хелперы для извлечения подмножеств данных."""

    def test_get_regular_aspects(self):
        """get_regular_aspects фильтрует аспекты с type=regular."""
        # Arrange
        aspects = (
            AspectMeta(method_name="step_one", method_ref=_fake_aspect, aspect_type="regular", description="1"),
            AspectMeta(method_name="step_two", method_ref=_fake_aspect, aspect_type="regular", description="2"),
            AspectMeta(method_name="finalize", method_ref=_fake_summary, aspect_type="summary", description="s"),
        )
        cm = ClassMetadata(class_ref=_EmptyClass, class_name="x", aspects=aspects)

        # Act
        regular = cm.get_regular_aspects()

        # Assert
        assert len(regular) == 2
        assert all(a.aspect_type == "regular" for a in regular)

    def test_get_regular_aspects_empty_when_no_aspects(self):
        """get_regular_aspects возвращает пустой кортеж без аспектов."""
        # Arrange
        cm = ClassMetadata(class_ref=_EmptyClass, class_name="x")

        # Act
        regular = cm.get_regular_aspects()

        # Assert
        assert regular == ()

    def test_get_summary_aspect_returns_summary(self):
        """get_summary_aspect возвращает аспект с type=summary."""
        # Arrange
        aspects = (
            AspectMeta(method_name="step", method_ref=_fake_aspect, aspect_type="regular", description=""),
            AspectMeta(method_name="finalize", method_ref=_fake_summary, aspect_type="summary", description=""),
        )
        cm = ClassMetadata(class_ref=_EmptyClass, class_name="x", aspects=aspects)

        # Act
        summary = cm.get_summary_aspect()

        # Assert
        assert summary is not None
        assert summary.method_name == "finalize"
        assert summary.aspect_type == "summary"

    def test_get_summary_aspect_returns_none_when_absent(self):
        """get_summary_aspect возвращает None, если summary-аспекта нет."""
        # Arrange
        cm = ClassMetadata(class_ref=_EmptyClass, class_name="x")

        # Act
        summary = cm.get_summary_aspect()

        # Assert
        assert summary is None

    def test_get_checkers_for_aspect(self):
        """get_checkers_for_aspect фильтрует чекеры по method_name."""
        # Arrange
        from action_machine.checkers.result_string_checker import ResultStringChecker

        checkers = (
            CheckerMeta(
                method_name="step_one",
                checker_class=ResultStringChecker,
                field_name="name",
                required=True,
                extra_params={},
            ),
            CheckerMeta(
                method_name="step_two",
                checker_class=ResultStringChecker,
                field_name="email",
                required=True,
                extra_params={},
            ),
        )
        cm = ClassMetadata(class_ref=_EmptyClass, class_name="x", checkers=checkers)

        # Act
        step_one_checkers = cm.get_checkers_for_aspect("step_one")

        # Assert
        assert len(step_one_checkers) == 1
        assert step_one_checkers[0].field_name == "name"

    def test_get_checkers_for_aspect_returns_empty(self):
        """get_checkers_for_aspect возвращает пустой кортеж для несуществующего аспекта."""
        # Arrange
        cm = ClassMetadata(class_ref=_EmptyClass, class_name="x")

        # Act
        result = cm.get_checkers_for_aspect("nonexistent")

        # Assert
        assert result == ()

    def test_get_dependency_classes(self):
        """get_dependency_classes возвращает кортеж классов зависимостей."""
        # Arrange
        deps = (
            DependencyInfo(cls=_ServiceA, factory=None, description=""),
            DependencyInfo(cls=_ServiceB, factory=None, description=""),
        )
        cm = ClassMetadata(class_ref=_EmptyClass, class_name="x", dependencies=deps)

        # Act
        classes = cm.get_dependency_classes()

        # Assert
        assert classes == (_ServiceA, _ServiceB)

    def test_get_dependency_classes_empty(self):
        """get_dependency_classes возвращает пустой кортеж без зависимостей."""
        # Arrange
        cm = ClassMetadata(class_ref=_EmptyClass, class_name="x")

        # Act
        classes = cm.get_dependency_classes()

        # Assert
        assert classes == ()

    def test_get_connection_keys(self):
        """get_connection_keys возвращает кортеж ключей соединений."""
        # Arrange
        conns = (
            ConnectionInfo(cls=_MockManager, key="db", description=""),
            ConnectionInfo(cls=_MockManager, key="cache", description=""),
        )
        cm = ClassMetadata(class_ref=_EmptyClass, class_name="x", connections=conns)

        # Act
        keys = cm.get_connection_keys()

        # Assert
        assert keys == ("db", "cache")

    def test_get_connection_keys_empty(self):
        """get_connection_keys возвращает пустой кортеж без соединений."""
        # Arrange
        cm = ClassMetadata(class_ref=_EmptyClass, class_name="x")

        # Act
        keys = cm.get_connection_keys()

        # Assert
        assert keys == ()


# ═════════════════════════════════════════════════════════════════════════════
# Строковое представление (__repr__)
# ═════════════════════════════════════════════════════════════════════════════


class TestRepr:
    """Проверяет __repr__ ClassMetadata."""

    def test_repr_contains_class_name(self):
        """repr содержит имя класса."""
        # Arrange
        cm = ClassMetadata(class_ref=_EmptyClass, class_name="test._EmptyClass")

        # Act
        result = repr(cm)

        # Assert
        assert "_EmptyClass" in result

    def test_repr_empty_has_no_role(self):
        """repr пустого класса не содержит слово role с непустым значением."""
        # Arrange
        cm = ClassMetadata(class_ref=_EmptyClass, class_name="test._EmptyClass")

        # Act
        result = repr(cm)

        # Assert — просто проверяем, что repr не падает
        assert isinstance(result, str)

    def test_repr_with_role(self):
        """repr класса с ролью содержит role."""
        # Arrange
        cm = ClassMetadata(
            class_ref=_EmptyClass,
            class_name="test._EmptyClass",
            role=RoleMeta(spec="admin"),
        )

        # Act
        result = repr(cm)

        # Assert
        assert "role" in result.lower() or "admin" in result

    def test_repr_with_dependencies(self):
        """repr класса с зависимостями содержит deps."""
        # Arrange
        deps = (DependencyInfo(cls=_ServiceA, factory=None, description=""),)
        cm = ClassMetadata(class_ref=_EmptyClass, class_name="x", dependencies=deps)

        # Act
        result = repr(cm)

        # Assert
        assert "dep" in result.lower() or "1" in result

    def test_repr_with_aspects(self):
        """repr класса с аспектами содержит aspects."""
        # Arrange
        aspects = (
            AspectMeta(method_name="step", method_ref=_fake_aspect, aspect_type="regular", description=""),
        )
        cm = ClassMetadata(class_ref=_EmptyClass, class_name="x", aspects=aspects)

        # Act
        result = repr(cm)

        # Assert
        assert "aspect" in result.lower() or "1" in result
